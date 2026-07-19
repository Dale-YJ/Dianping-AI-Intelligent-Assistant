"""Query rewriting service — maps abstract user queries to concrete Yelp search conditions.

Users often search with abstract descriptions ("romantic date", "quiet workspace",
"cheap eats") that don't match Yelp's concrete category names (Italian, Sushi Bars,
Cafes). This module uses the LLM to translate abstract intent into concrete
OpenSearch filter conditions before the retrieval step.

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

YELP_CATEGORY_CONTEXT = """## Yelp Category Distribution (from the actual dataset)

### CUISINE TYPES
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

REWRITE_SYSTEM_PROMPT = """You are a search query optimizer for a Yelp-based restaurant recommendation system. Your job is to convert vague, abstract, or emotional user queries into concrete, searchable conditions.

The Yelp dataset categories are CONCRETE business types (Italian, Sushi Bars, Cafes, etc.) — they do NOT contain abstract adjectives like "romantic", "quiet", "trendy", "authentic", "cheap".

Given a user query, you must:
1. Map abstract descriptors to REAL Yelp categories
2. Suggest appropriate star rating filters
3. Output structured JSON that can be fed directly into an OpenSearch query

CRITICAL RULES:
- ONLY use categories that actually appear in the Yelp category list below
- If a concept doesn't map to any real category, use star rating + keyword hints instead
- The "keywords" field should contain concrete search terms, NOT the original abstract words
- Leave "categories" as an empty list if no single category captures the intent"""

REWRITE_USER_PROMPT_TEMPLATE = """{category_context}

---

User query: "{query}"

Analyze the query and output a JSON object with these fields:
- "is_specific": true if the query already contains concrete restaurant/cuisine names, false if it's abstract
- "categories": list of actual Yelp categories to filter by (empty list if none match well)
- "stars_min": minimum star rating (1.0-5.0, use null if no preference)
- "stars_max": maximum star rating (1.0-5.0, null if no preference)
- "keywords": 3-5 concrete search keywords that would match business names, review text, or attributes (e.g., "candlelit", "outdoor patio", "quiet atmosphere", "affordable lunch") — use English terms matching the Yelp domain
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
        - ``categories`` (list[str]): Yelp categories to filter by
        - ``stars_min`` (float | None): Minimum star rating
        - ``stars_max`` (float | None): Maximum star rating
        - ``keywords`` (list[str]): Concrete search keywords
        - ``explanation`` (str): Human-readable reasoning

        On failure, returns a fallback dict that passes the original query
        through unchanged.
    """
    fallback = {
        "is_specific": False,
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
        return {
            "is_specific": bool(result.get("is_specific", False)),
            "categories": _normalize_list(result.get("categories", [])),
            "stars_min": _normalize_rating(result.get("stars_min")),
            "stars_max": _normalize_rating(result.get("stars_max")),
            "keywords": _normalize_list(result.get("keywords", [query])),
            "explanation": str(result.get("explanation", "")),
        }

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse query rewrite JSON: {e}, content={content[:200]}")
        fallback["keywords"] = [query]
        return fallback
    except Exception as e:
        logger.error(f"Query rewriting failed: {e}")
        fallback["keywords"] = [query]
        return fallback


def build_search_query(rewritten: dict[str, Any]) -> str:
    """Convert a rewritten query dict into a single search string for hybrid_search.

    This combines categories and keywords into a single string that works well
    with both BM25 (text match) and vector (semantic) retrieval.

    Args:
        rewritten: The dict returned by :func:`rewrite_query`.

    Returns:
        A search string like ``"Italian Steakhouses Wine Bars | intimate candlelit fine dining"``.
    """
    parts: list[str] = []

    categories = rewritten.get("categories", [])
    if categories:
        parts.append(" ".join(categories))

    keywords = rewritten.get("keywords", [])
    if keywords:
        parts.append(" ".join(keywords))

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
