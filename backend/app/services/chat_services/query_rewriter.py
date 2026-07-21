"""Query rewriting service — maps abstract user queries to concrete search conditions.

Users often search with abstract descriptions ("romantic date", "quiet workspace",
"cheap eats") that don't match concrete business categories. This module uses the
LLM to translate abstract intent into concrete OpenSearch filter conditions.

The index now contains BOTH Yelp (US) data and Dianping (Chinese city) data:
  - Chinese cities available: 北京, 成都, 广州, 上海
  - Chinese cuisine types: 川菜, 粤菜, 火锅, 烤鸭, 湘菜, 云南菜, etc.

Architecture:
    Raw query → LLM rewrites → structured search params → hybrid_search()
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.app.services.llm_client import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# Yelp category context — sampled from the actual 5k-business dataset
# Organized by type so the LLM can map abstract intent → real categories
# ────────────────────────────────────────────────────────────────

YELP_CATEGORY_CONTEXT = """## Category Distribution (from the actual dataset — both Yelp US + Dianping China)

### CHINESE CITY DATA (大众点评 — 北京/成都/广州/上海)
  Available cities: 北京(45), 成都(45), 广州(45), 上海(45)
  Chinese cuisine types in the index:
    川菜/四川火锅(30+), 粤菜/粤式茶点(20+), 烤鸭/京菜(20+), 湘菜(10+),
    云南菜|滇菜(10+), 日本料理(30+), 西餐(30+), 意大利菜(10+),
    老北京火锅(15+), 韩式料理(10+), 面馆(10+), 新疆菜(5+),
    苏浙菜/淮扬菜(10+), 潮汕菜(5+), 内蒙菜(5+), 素食(5+),
    鲁菜(5+), 私房菜(5+), 火锅自助(5+), 农家菜(5+), 烧烤(5+)

### US YELP — CUISINE TYPES
  Italian(160), Mexican(150), Chinese(111), Japanese(76), Sushi Bars(61),
  Steakhouses(55), Asian Fusion(47), Mediterranean(36), Thai(37), Indian(34),
  Vietnamese(31), Korean(13), French(16), Greek(29), Cajun/Creole(33),
  Southern(33), Barbeque(58), Latin American(25), Caribbean(29),
  Tex-Mex(32), Cuban(12), Middle Eastern(13), Pakistani(12),
  Canadian (New)(13), Ethnic Food(15)

### FOOD TYPES
  Pizza(250), Burgers(183), Sandwiches(279), Seafood(121), Salad(112),
  Chicken Wings(91), Hot Dogs(22), Tacos(40), Noodles(19), Soup(24),
  Cheesesteaks(24), Bagels(31), Wraps(12), Buffets(16), Fast Food(218),
  Delis(79), Diners(47), Food Trucks(55), Street Vendors(12),
  Comfort Food(23), Soul Food(16), Vegetarian(30), Vegan(22), Gluten-Free(26)

### DINING & DRINKS
  Restaurants(1762), Bars(373), Coffee & Tea(251), Breakfast & Brunch(218),
  Bakeries(102), Desserts(94), Ice Cream & Frozen Yogurt(66), Cafes(105),
  Pubs(73), Sports Bars(65), Cocktail Bars(60), Lounges(44), Wine Bars(40),
  Beer Bar(37), Dive Bars(25), Gastropubs(19), Breweries(47), Wineries(13),
  Brewpubs(15), Juice Bars & Smoothies(58), Bubble Tea(14), Coffee Roasteries(12),
  Donuts(42), Cupcakes(12)

### AMBIANCE / EXPERIENCE-RELATED (embedded in attributes & categories)
  Romantic: Fine Dining implied by Steakhouses, French, Italian, Wine Bars,
    Cocktail Bars, Lounges — filter on higher stars (≥4.0) + attributes
  Quiet/Workspace: Cafes, Coffee & Tea, Bakeries, Bookstores(15), Libraries
  Lively/Energetic: Sports Bars, Dance Clubs(14), Music Venues(46), Karaoke(11),
    Jazz & Blues(12), Festivals(15)
  Outdoor: Parks(39), Farmers Market(14), Food Trucks(55), Outdoor Gear(21), Boating(14)
  Upscale/Luxury: Steakhouses, French, Wine Bars, Fine Dining
  Casual: Fast Food, Diners, Pubs, Food Trucks, Delis, Sandwiches, Pizza

### ATTRACTIONS & ACTIVITIES
  Arts & Entertainment(206), Music Venues(46), Cinema(13), Museums(15),
  Performing Arts(22), Art Galleries(30), Active Life(286), Gyms(61), Yoga(36),
  Golf(18), Parks(39), Festivals(15), Boating(14), Recreation Centers(13),
  Playgrounds(13), Dance Clubs(14)

### SERVICES
  Beauty & Spas(485), Home Services(466), Automotive(350), Health & Medical(372),
  Event Planning & Services(326), Hotels & Travel(196), Education(65),
  Professional Services(100), Financial Services(45), Real Estate(113)
"""

REWRITE_SYSTEM_PROMPT = """You are a search query optimizer for a restaurant recommendation system covering BOTH US Yelp data AND Chinese Dianping (大众点评) data for four cities: 北京(Beijing), 成都(Chengdu), 广州(Guangzhou), 上海(Shanghai).

The index contains both English Yelp businesses and Chinese Dianping restaurants. Both use the SAME field names: "name", "categories", "stars", "city", "review_count".

Given a user query, you must:
1. Detect if the user is asking about a specific Chinese city (北京/成都/广州/上海) or Chinese cuisine
2. Map abstract descriptors to REAL categories from BOTH datasets
3. Suggest appropriate star rating filters
4. Output structured JSON that can be fed directly into an OpenSearch query

CRITICAL RULES:
- If the user mentions a Chinese city (北京/成都/广州/上海), ALWAYS include the city name in BOTH Chinese AND English in the keywords (e.g., "北京 Beijing")
- For Chinese cuisine queries, use Chinese category terms (川菜、粤菜、火锅、烤鸭 etc.) that match the actual data
- The "keywords" field should contain BOTH English AND Chinese search terms when the user writes in Chinese
- Leave "categories" as an empty list if no single category captures the intent perfectly
- Output ONLY the JSON object, nothing else."""

REWRITE_USER_PROMPT_TEMPLATE = """{category_context}

---

User query: "{query}"

Analyze the query and output a JSON object with these fields:
- "is_specific": true if the query already contains concrete restaurant/cuisine names, false if it's abstract
- "city": if the user specifies a Chinese city (北京/成都/广州/上海), output the city name in Chinese (e.g., "北京"); if they specify a US city, output the English name (e.g., "Philadelphia"); use null if no city is mentioned
- "categories": list of actual categories to filter by (may be Chinese like "川菜" or English like "Italian" — use what matches the data; empty list if none match well)
- "stars_min": minimum star rating (1.0-5.0, use null if no preference)
- "stars_max": maximum star rating (1.0-5.0, null if no preference)
- "keywords": 3-5 concrete search keywords — use the SAME LANGUAGE as the user's query. DO NOT include the city name in keywords (city is handled separately). Examples: "烤鸭 京菜", "火锅 四川火锅", "quiet romantic candlelit Italian"
- "explanation": one short sentence explaining your reasoning

Output ONLY the JSON object, nothing else."""


async def rewrite_query(query: str) -> dict[str, Any]:
    """Rewrite an abstract user query into concrete Yelp search parameters.

    Args:
        query: The raw user query (may contain abstract descriptors like
               "romantic", "quiet", "cheap", "authentic").

    Returns:
        A dict with keys:
        - ``is_specific`` (bool): Whether the original query was already concrete
        - ``city`` (str | None): Detected city name (Chinese or English), or None
        - ``categories`` (list[str]): Categories to filter by
        - ``stars_min`` (float | None): Minimum star rating
        - ``stars_max`` (float | None): Maximum star rating
        - ``keywords`` (list[str]): Concrete search keywords (city excluded)
        - ``explanation`` (str): Human-readable reasoning

        On failure, returns a fallback dict that passes the original query
        through unchanged.
    """
    fallback = {
        "is_specific": False,
        "city": (extract_city_hints(query) or [None])[0],
        "categories": [],
        "stars_min": None,
        "stars_max": None,
        "keywords": [query],
        "explanation": "Query rewriting unavailable; using original query.",
    }

    try:
        llm = get_llm()
        prompt = REWRITE_USER_PROMPT_TEMPLATE.format(
            category_context=YELP_CATEGORY_CONTEXT,
            query=query,
        )
        messages = [
            SystemMessage(content=REWRITE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info(f"Rewriting query: {query[:100]}")
        response = await llm.ainvoke(messages)
        content = response.content or ""

        # Parse JSON from the response (handle markdown fences)
        content = content.strip()
        if content.startswith("```"):
            # Remove ```json or ``` fences
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        result = json.loads(content)

        # Validate and normalize
        result = {
            "is_specific": bool(result.get("is_specific", False)),
            "city": _normalize_city(result.get("city")),
            "categories": _normalize_list(result.get("categories", [])),
            "stars_min": _normalize_rating(result.get("stars_min")),
            "stars_max": _normalize_rating(result.get("stars_max")),
            "keywords": _normalize_list(result.get("keywords", [query])),
            "explanation": str(result.get("explanation", "")),
        }

        # Safety net: if LLM didn't detect a city but the original query
        # contains one, inject it from extract_city_hints
        if not result["city"]:
            hints = extract_city_hints(query)
            if hints:
                result["city"] = hints[0]  # take the first detected city

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse query rewrite JSON: {e}, content={content[:200]}")
        fallback["keywords"] = [query]
        return fallback
    except Exception as e:
        logger.error(f"Query rewriting failed: {e}")
        fallback["keywords"] = [query]
        return fallback


# Chinese city names that exist in the index — used to detect location intent
CHINESE_CITIES = {
    "北京": "北京", "beijing": "北京", "Beijing": "北京",
    "成都": "成都", "chengdu": "成都", "Chengdu": "成都",
    "广州": "广州", "guangzhou": "广州", "Guangzhou": "广州",
    "上海": "上海", "shanghai": "上海", "Shanghai": "上海",
}


def extract_city_hints(query: str) -> list[str]:
    """Extract Chinese city names from the raw user query.

    This is a safety net — even if the LLM rewriter drops the city,
    we still inject it into the search keywords so city-specific
    results appear.

    Args:
        query: The raw user query string.

    Returns:
        List of city names found in the query (e.g., ``["北京"]``).
    """
    found = []
    query_lower = query.lower()
    for key, city in CHINESE_CITIES.items():
        if key.lower() in query_lower and city not in found:
            found.append(city)
    return found


def build_search_query(rewritten: dict[str, Any], original_query: str = "") -> str:
    """Convert a rewritten query dict into a single search string for hybrid_search.

    Automatically appends any Chinese city names found in the original query
    to ensure location-specific results are not lost during rewriting.

    Args:
        rewritten: The dict returned by :func:`rewrite_query`.
        original_query: The raw user query (used to extract city hints).

    Returns:
        A search string like ``"川菜 火锅 | 成都"``.
    """
    parts: list[str] = []

    categories = rewritten.get("categories", [])
    if categories:
        parts.append(" ".join(categories))

    keywords = rewritten.get("keywords", [])
    if keywords:
        parts.append(" ".join(keywords))

    # Safety net: if the original query mentions a Chinese city,
    # ensure it appears in the search string
    if original_query:
        city_hints = extract_city_hints(original_query)
        existing = " ".join(parts).lower()
        for city in city_hints:
            if city.lower() not in existing:
                parts.append(city)

    return " | ".join(parts) if parts else ""


# ────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────

def _normalize_list(value: Any) -> list[str]:
    """Ensure value is a list of non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if v and str(v).strip()]


def _normalize_rating(value: Any) -> float | None:
    """Ensure value is a valid rating between 1.0 and 5.0, or None."""
    if value is None:
        return None
    try:
        v = float(value)
        if 1.0 <= v <= 5.0:
            return v
    except (TypeError, ValueError):
        pass
    return None


def _normalize_city(value: Any) -> str | None:
    """Ensure value is a valid known city name, or None."""
    if not value or not isinstance(value, str):
        return None
    city = value.strip()
    # Check if it's one of our known Chinese cities
    for known in CHINESE_CITIES.values():
        if city == known:
            return city
    # For non-Chinese cities, return the value as-is if it looks valid
    if len(city) >= 2 and not city.startswith("null"):
        return city
    return None
