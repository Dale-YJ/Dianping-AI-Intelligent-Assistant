"""RAG service — orchestrates retrieval + LLM generation with streaming.

This module ties together the separated concerns:
- ``llm_client`` — LLM connection
- ``conversation`` — multi-turn history
- ``prompts`` — prompt engineering
- ``search_service`` — OpenSearch retrieval
- ``query_rewriter`` — LLM-based query → concrete search conditions
- ``reranker`` — embedding-similarity re-ranking (bge-base-zh-v1.5)
- ``user_profile`` — user preference learning from conversation history

Pipeline (updated):
    1. Load user profile from conversation history
    2. User query → rewrite_query() → concrete keywords + categories
    3. hybrid_search() with expanded candidate pool
    4. rerank() with bge-reranker-v2-m3 cross-encoder
    5. build_context() → LLM streaming → recommendations
    6. Analyze conversation → update user profile
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from backend.app.schemas.chat_schemas.schemas import RecommendationItem, SourceInfo
from .conversation import (
    add_message,
    get_history,
    get_or_create_conversation,
)
from backend.app.services.llm_client import get_llm
from .prompts import (
    SYSTEM_PROMPT,
    BUSINESS_ANALYSIS_SYSTEM_PROMPT,
    build_context,
    build_user_prompt,
    build_business_analysis_prompt,
)
from .query_rewriter import rewrite_query, build_search_query
from .user_profile import (
    get_user_profile,
    format_profile_for_prompt,
)
from .profile_analyzer import analyze_conversation_for_profile

# 统一使用 base_config 的 OpenSearch 客户端和检索接口
from opensearch_client import get_opensearch_client
from retrieve import hybrid_search
from reranker import rerank

logger = logging.getLogger(__name__)

BUSINESS_INDEX = "yelp_business"
REVIEW_INDEX = "yelp_review"

# ── Cuisine alias mapping ───────────────────────────────────
# Common abbreviations → full cuisine names found in actual data.
# Used by _apply_cuisine_boost() to match user intent with
# business categories when there's a semantic gap.

CUISINE_ALIASES: dict[str, list[str]] = {
    "日料": ["日本料理", "日式料理", "日料"],
    "韩料": ["韩式料理", "韩国料理", "韩式烤肉"],
    "川菜": ["川菜", "川菜馆", "四川菜", "四川火锅"],
    "湘菜": ["湘菜", "湖南菜"],
    "粤菜": ["粤菜", "粤菜馆", "广东菜", "粤式茶点", "茶餐厅"],
    "火锅": ["火锅", "四川火锅", "老北京火锅", "火锅自助", "川味火锅"],
    "烤鸭": ["烤鸭", "京菜"],
    "面馆": ["面馆", "面", "粉面馆", "重庆小面"],
    "西餐": ["西餐", "意大利菜", "法国菜"],
    "烧烤": ["烧烤", "烤肉"],
    "本帮菜": ["本帮菜", "上海菜"],
    "云南菜": ["云南菜", "滇菜"],
    "新疆菜": ["新疆菜"],
    "苏浙菜": ["苏浙菜", "淮扬菜", "江浙菜", "浙菜"],
    "鲁菜": ["鲁菜"],
    "素食": ["素食", "素菜"],
    "潮汕菜": ["潮汕菜", "潮州菜"],
    "内蒙菜": ["内蒙菜"],
    "私房菜": ["私房菜"],
    "农家菜": ["农家菜"],
    "小吃": ["小吃", "快餐简餐", "粉面馆"],
    "海鲜": ["海鲜", "海鲜火锅"],
    "自助": ["自助", "自助餐", "火锅自助"],
    "咖啡": ["咖啡", "咖啡厅", "面包甜点"],
    "甜品": ["甜品", "面包甜点", "蛋糕", "冰淇淋"],
}

# Boost multipliers
CUISINE_MATCH_BOOST = 2.0     # score multiplier when cuisine matches
CUISINE_MISMATCH_PENALTY = 0.5  # score multiplier when cuisine requested but no match

# Reranker settings
RERANK_CANDIDATE_MULTIPLIER = 4  # fetch top_k * N candidates, rerank, then trim
RERANK_MIN_POOL_SIZE = 15        # minimum candidates before reranking


def _search_businesses(
    query: str,
    top_k: int = 5,
    min_score: float = 0.3,
    filter_clauses: list[dict] | None = None,
) -> list[dict]:
    """混合搜索商家，底层调 retrieve.hybrid_search，加 min_score 截断。"""
    results = hybrid_search(
        query, k=max(top_k * 2, 10),
        index_name=BUSINESS_INDEX,
        filter_clauses=filter_clauses,
    )
    return [r for r in results if r.get("_score", 0) >= min_score][:top_k]


def _search_businesses_via_reviews(
    query: str,
    top_k: int = 10,
    min_score: float = 0.3,
    filter_clauses: list[dict] | None = None,
) -> list[dict]:
    """Search reviews for the query, then aggregate to unique businesses.

    This captures businesses whose *reviews* match the query semantically
    (e.g. "romantic atmosphere", "quiet workspace") even when their category
    labels don't (e.g. a restaurant tagged only "Italian" but reviewed as
    "perfect romantic date night").

    Pipeline:
        1. hybrid_search on yelp_review index
        2. Group by business_id, keeping best score per business
        3. Fetch full business documents for the top N

    Args:
        query: The search string (ideally already rewritten).
        top_k: Max number of unique businesses to return.
        min_score: Minimum hybrid-search score for a review to be considered.

    Returns:
        Business documents with ``_score`` set to their best review score
        and ``_match_source`` set to ``"reviews"``.
    """
    client = get_opensearch_client()

    # Check if review index exists
    try:
        if not client.indices.exists(index=REVIEW_INDEX):
            return []
    except Exception:
        return []

    # 1. Search reviews with expanded pool (reviews are noisy, need more candidates)
    review_pool_size = top_k * 6
    try:
        review_results = hybrid_search(
            query,
            k=review_pool_size,
            index_name=REVIEW_INDEX,
            filter_clauses=filter_clauses,
        )
    except Exception:
        logger.warning("Review search failed, skipping review-based discovery")
        return []

    review_results = [r for r in review_results if r.get("_score", 0) >= min_score]

    if not review_results:
        return []

    # 2. Group by business_id — keep best score, count mentions
    biz_scores: dict[str, float] = {}
    biz_mentions: dict[str, int] = {}
    for review in review_results:
        biz_id = review.get("business_id", "")
        if not biz_id:
            continue
        score = review.get("_score", 0)
        biz_mentions[biz_id] = biz_mentions.get(biz_id, 0) + 1
        if score > biz_scores.get(biz_id, 0):
            biz_scores[biz_id] = score

    # Sort by score descending, take top_k
    sorted_biz_ids = sorted(
        biz_scores.keys(),
        key=lambda bid: (biz_scores[bid], biz_mentions.get(bid, 0)),
        reverse=True,
    )[:top_k]

    # 3. Fetch full business documents
    businesses: list[dict] = []
    for biz_id in sorted_biz_ids:
        try:
            resp = client.get(index=BUSINESS_INDEX, id=biz_id, ignore=[404])
            if resp.get("found"):
                biz = dict(resp["_source"])
                biz["_score"] = biz_scores[biz_id]
                biz["_match_source"] = "reviews"
                biz["_review_mentions"] = biz_mentions.get(biz_id, 0)
                businesses.append(biz)
        except Exception:
            pass

    logger.info(
        f"Review-based discovery: {len(review_results)} reviews → "
        f"{len(sorted_biz_ids)} unique businesses, fetched {len(businesses)}"
    )

    return businesses


# ═══════════════════════════════════════════════════════════════
# Cuisine boost — post-search score adjustment
# ═══════════════════════════════════════════════════════════════

def _detect_cuisine_intent(query: str, rewritten_categories: list[str]) -> list[str]:
    """Detect which cuisine aliases the user is asking about.

    Checks both the original query and the LLM-rewritten categories against
    CUISINE_ALIASES keys. Returns the set of alias group keys that match
    (e.g. ``["日料", "川菜"]``).

    Args:
        query: The original user query.
        rewritten_categories: Categories extracted by the query rewriter.

    Returns:
        List of matched alias keys, or empty list if no cuisine intent detected.
    """
    matched: list[str] = []
    combined = query + " " + " ".join(rewritten_categories)
    for alias_key in CUISINE_ALIASES:
        if alias_key in combined:
            matched.append(alias_key)
    # Also check full-form aliases in the query (e.g. user typed "日本料理" directly)
    if not matched:
        for alias_key, aliases in CUISINE_ALIASES.items():
            for full_form in aliases:
                if full_form in combined:
                    matched.append(alias_key)
                    break
    return matched


def _apply_cuisine_boost(
    candidates: list[dict],
    cuisine_keys: list[str],
) -> list[dict]:
    """Apply cuisine match boost / mismatch penalty to candidate scores.

    For each candidate, checks whether its ``categories`` field contains
    any of the full-form aliases for the detected cuisine intent. Matching
    candidates get their ``_score`` multiplied by ``CUISINE_MATCH_BOOST``;
    non-matching candidates get ``CUISINE_MISMATCH_PENALTY``.

    If ``cuisine_keys`` is empty (no cuisine intent detected), candidates
    are returned unchanged.

    Args:
        candidates: Business documents from search, each with ``_score``.
        cuisine_keys: Alias keys detected by :func:`_detect_cuisine_intent`.

    Returns:
        Candidates with adjusted ``_score`` values, re-sorted descending.
    """
    if not cuisine_keys or not candidates:
        return candidates

    # Collect all full-form category names for the matched aliases
    target_categories: set[str] = set()
    for key in cuisine_keys:
        aliases = CUISINE_ALIASES.get(key, [])
        target_categories.update(aliases)

    logger.info(
        f"Cuisine boost: intent={cuisine_keys}, "
        f"target_categories={target_categories}"
    )

    for doc in candidates:
        doc_categories = doc.get("categories", "")
        matched = any(
            cat in doc_categories
            for cat in target_categories
        )
        if matched:
            doc["_score"] *= CUISINE_MATCH_BOOST
            doc["_cuisine_match"] = True
        else:
            doc["_score"] *= CUISINE_MISMATCH_PENALTY
            doc["_cuisine_match"] = False

    # Re-sort by adjusted score
    candidates.sort(key=lambda d: d.get("_score", 0), reverse=True)

    boost_stats = {
        "matched": sum(1 for d in candidates if d.get("_cuisine_match")),
        "penalized": sum(1 for d in candidates if not d.get("_cuisine_match")),
    }
    logger.info(f"Cuisine boost applied: {boost_stats}")

    return candidates


async def _search_with_rewrite_and_rerank(
    query: str,
    top_k: int = 5,
    min_score: float = 0.3,
) -> list[dict]:
    """Full search pipeline: rewrite → hybrid search → rerank.

    1. LLM rewrites abstract queries into concrete categories + keywords
    2. Hybrid search fetches an expanded candidate pool
    3. Cross-encoder reranker scores and re-sorts candidates
    4. Trim to top_k

    Args:
        query: Raw user query (may contain abstract descriptors).
        top_k: Number of final results to return.
        min_score: Minimum hybrid-search score for candidate inclusion.

    Returns:
        Re-ranked business documents (up to ``top_k``).
    """
    # --- Step 1: Query rewriting ---
    rewritten = await rewrite_query(query)
    search_str = build_search_query(rewritten, original_query=query)

    # Build hard city filter — if user specified a city, force it in OpenSearch
    city_filter = rewritten.get("city")
    filter_clauses: list[dict] | None = None
    if city_filter:
        filter_clauses = [{"term": {"city.keyword": city_filter}}]

    logger.info(
        f"Query rewritten: is_specific={rewritten['is_specific']}, "
        f"city={city_filter}, "
        f"categories={rewritten['categories']}, keywords={rewritten['keywords']}, "
        f"search_str={search_str[:120]}"
    )

    # If the rewrite produced no useful keywords, fall back to original query
    if not search_str.strip():
        search_str = query

    # --- Step 2: Dual-path search ---
    # Path A: Direct business search (categories, name, attributes)
    # Path B: Review-based discovery (reviews → businesses)
    pool_size = max(top_k * RERANK_CANDIDATE_MULTIPLIER, RERANK_MIN_POOL_SIZE)

    biz_from_direct = hybrid_search(
        search_str, k=pool_size,
        index_name=BUSINESS_INDEX,
        filter_clauses=filter_clauses,
    )
    biz_from_direct = [r for r in biz_from_direct if r.get("_score", 0) >= min_score]
    for b in biz_from_direct:
        b["_match_source"] = "business"

    biz_from_reviews = _search_businesses_via_reviews(
        search_str, top_k=pool_size,
        filter_clauses=filter_clauses,
    )

    # Merge: review-discovered businesses first (more relevant for abstract queries),
    # then direct matches. Deduplicate by business_id.
    seen_ids: set[str] = set()
    candidates: list[dict] = []
    for biz in biz_from_reviews:
        bid = biz.get("business_id", "")
        if bid and bid not in seen_ids:
            seen_ids.add(bid)
            candidates.append(biz)
    for biz in biz_from_direct:
        bid = biz.get("business_id", "")
        if bid and bid not in seen_ids:
            seen_ids.add(bid)
            candidates.append(biz)

    logger.info(
        f"Dual-path search: {len(biz_from_direct)} direct + "
        f"{len(biz_from_reviews)} via reviews → "
        f"{len(candidates)} unique candidates"
    )

    if not candidates:
        logger.info("No candidates from either search path")
        return []

    # --- Step 3: Apply star rating filter (if LLM specified one) ---
    stars_min = rewritten.get("stars_min")
    stars_max = rewritten.get("stars_max")
    if stars_min is not None or stars_max is not None:
        filtered = []
        for doc in candidates:
            doc_stars = float(doc.get("stars", 0))
            if stars_min is not None and doc_stars < stars_min:
                continue
            if stars_max is not None and doc_stars > stars_max:
                continue
            filtered.append(doc)
        if filtered:
            candidates = filtered
        # If all candidates are filtered out, keep the original pool

    # --- Step 3.5: Cuisine boost/penalty ---
    # Detect cuisine intent from the query and boost matching businesses,
    # penalize non-matching ones. This handles abbreviated cuisine names
    # like "日料" → "日本料理" that the vector search usually catches
    # but may miss in edge cases.
    cuisine_keys = _detect_cuisine_intent(query, rewritten.get("categories", []))
    if cuisine_keys and len(candidates) > 1:
        candidates = _apply_cuisine_boost(candidates, cuisine_keys)

    if len(candidates) <= 1:
        # Too few to meaningfully rerank
        return candidates[:top_k]

    # --- Step 4: Rerank with cross-encoder ---
    # Use the original user query for reranker (semantically richer)
    try:
        candidates = rerank(query, candidates, top_k=top_k)
        if candidates:
            logger.info(
                f"Reranked: top score={candidates[0].get('_score', 0):.4f} "
                f"(hybrid was: {candidates[0].get('_rerank_score', 0):.4f})"
            )
    except Exception:
        logger.warning("Reranker unavailable, using hybrid search scores only")
        # Return top hybrid-search hits as-is
        candidates = candidates[:top_k]

    return candidates[:top_k]


def _search_reviews(business_id: str, top_k: int = 5) -> list[dict]:
    """按 business_id 查评价，按 useful 降序。"""
    client = get_opensearch_client()
    if not client.indices.exists(index=REVIEW_INDEX):
        return []
    body = {
        "size": top_k,
        "query": {"bool": {"must": [{"term": {"business_id": business_id}}]}},
        "sort": [{"useful": {"order": "desc"}}],
    }
    try:
        resp = client.search(index=REVIEW_INDEX, body=body)
    except Exception:
        return []
    return [h["_source"] for h in resp.get("hits", {}).get("hits", [])]


def _get_business_info(business_id: str) -> dict | None:
    """Get a single business document from OpenSearch by ID."""
    client = get_opensearch_client()
    try:
        resp = client.get(index=BUSINESS_INDEX, id=business_id, ignore=[404])
        if resp.get("found"):
            return dict(resp["_source"])
        return None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# Main RAG stream
# ═══════════════════════════════════════════════════════════════

async def rag_stream(
    query: str,
    conversation_id: str | None = None,
    business_id: str | None = None,
) -> AsyncIterator[str]:
    """Execute the full RAG pipeline and yield SSE-formatted strings.

    Two modes:
      - **User mode** (default): RAG search → LLM recommendation
      - **Business mode** (when ``business_id`` is set): fetch reviews → LLM analysis

    Pipeline steps (user mode):
    1. Resolve / create conversation
    2. Store user message
    3. Load user profile
    4. Search OpenSearch for matching businesses
    5. If no results → fallback with clarifying prompt
    6. Build RAG context + user prompt (with profile)
    7. Stream LLM response token-by-token
    8. Store assistant response
    9. Analyze conversation and update user profile
    10. Yield structured recommendations
    11. Signal completion

    Yields:
        SSE event strings (``data: {...}\n\n``).
    """
    conv_id = await get_or_create_conversation(conversation_id)

    # ── Business-side analysis path ──
    if business_id:
        async for event in _analyze_business_stream(query, conv_id, business_id):
            yield event
        return

    # 1. yield start event
    yield _sse("start", {"conversation_id": conv_id, "mode": "user"})

    # 2. store user message
    await add_message(conv_id, "user", query)

    # 3. Load user profile
    user_profile = await get_user_profile(conv_id)
    profile_text = format_profile_for_prompt(user_profile)

    # 4. search (with query rewriting + reranking)
    businesses = await _search_with_rewrite_and_rerank(query)

    # 5. no search results → let LLM chat naturally (handles greetings, small talk)
    if not businesses:
        history = await get_history(conv_id)
        chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add profile to system context if available
        if profile_text:
            chat_messages.append({"role": "system", "content": profile_text})

        for m in history[-6:]:
            chat_messages.append({"role": m["role"], "content": m["content"]})
        # Ensure the current user query is in the prompt (history[-6:] may truncate it)
        chat_messages.append({"role": "user", "content": query})

        llm = get_llm()
        full_response = ""
        try:
            async for chunk in llm.astream(chat_messages):
                if chunk.content:
                    full_response += chunk.content
                    yield _sse("delta", {"content": chunk.content})
        except Exception:
            full_response = "你好！我是大众点评 AI 小探 🍴 告诉我你想吃什么，我帮你找最合适的餐厅～"
            yield _sse("delta", {"content": full_response})

        await add_message(conv_id, "assistant", full_response)

        # Analyze and update user profile
        try:
            profile_data = await analyze_conversation_for_profile(query, full_response)
            if any([
                profile_data.get("locations"),
                profile_data.get("cuisine_preferences"),
                profile_data.get("taste_preferences"),
                profile_data.get("dining_scenarios"),
                profile_data.get("budget_level"),
                profile_data.get("other_keywords"),
            ]):
                from .user_profile import update_user_profile
                await update_user_profile(conv_id, profile_data)
                logger.info(f"Updated user profile for conversation {conv_id}")
        except Exception as e:
            logger.warning(f"Failed to update user profile: {e}")

        yield f"data: {{\"type\": \"recommendations\", \"items\": []}}\n\n"
        yield _sse("done", {"total_tokens": len(full_response)})
        return

    # 6. build context & prompt (with profile)
    context = build_context(businesses)
    history = await get_history(conv_id)
    user_prompt = build_user_prompt(query, context, history, profile_text)

    # 7. prepare structured recommendations
    recs = _build_recommendations(businesses)

    # 8. stream LLM response
    llm = get_llm()
    full_response = ""

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                yield _sse("delta", {"content": chunk.content})

    except Exception as e:
        error_msg = f"抱歉，AI 服务暂时不可用，请稍后重试。({e})"
        full_response = error_msg
        yield _sse("delta", {"content": error_msg})

    # 9. store assistant response
    await add_message(conv_id, "assistant", full_response)

    # 10. Analyze conversation and update user profile
    try:
        profile_data = await analyze_conversation_for_profile(query, full_response)
        if any([
            profile_data.get("locations"),
            profile_data.get("cuisine_preferences"),
            profile_data.get("taste_preferences"),
            profile_data.get("dining_scenarios"),
            profile_data.get("budget_level"),
            profile_data.get("other_keywords"),
        ]):
            from .user_profile import update_user_profile
            await update_user_profile(conv_id, profile_data)
            logger.info(f"Updated user profile for conversation {conv_id}")
    except Exception as e:
        logger.warning(f"Failed to update user profile: {e}")

    # 11. yield recommendations
    recs_json = json.dumps(
        [r.model_dump() for r in recs], ensure_ascii=False
    )
    yield f"data: {{\"type\": \"recommendations\", \"items\": {recs_json}}}\n\n"

    # 12. done
    yield _sse("done", {"total_tokens": len(full_response)})


# ═══════════════════════════════════════════════════════════════
# Non-streaming generation (fallback / debug)
# ═══════════════════════════════════════════════════════════════

async def rag_generate(
    query: str,
    conversation_id: str | None = None,
    business_id: str | None = None,
) -> tuple[str, str, list[RecommendationItem]]:
    """Non-streaming RAG: returns (conversation_id, text, recommendations).

    Two modes:
      - **User mode** (default): RAG search → LLM recommendation
      - **Business mode** (when ``business_id`` is set): fetch reviews → LLM analysis

    Useful for debugging or batch processing where streaming is unnecessary.
    """
    conv_id = await get_or_create_conversation(conversation_id)

    # ── Business-side analysis path ──
    if business_id:
        return await _analyze_business_generate(query, conv_id, business_id)

    # Load user profile
    user_profile = await get_user_profile(conv_id)
    profile_text = format_profile_for_prompt(user_profile)

    # search (with query rewriting + reranking)
    businesses = await _search_with_rewrite_and_rerank(query)

    if not businesses:
        history = await get_history(conv_id)
        chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add profile to system context if available
        if profile_text:
            chat_messages.append({"role": "system", "content": profile_text})

        for m in history[-6:]:
            chat_messages.append({"role": m["role"], "content": m["content"]})
        # Ensure the current user query is in the prompt (history[-6:] may truncate it)
        chat_messages.append({"role": "user", "content": query})

        await add_message(conv_id, "user", query)
        llm = get_llm()
        try:
            resp = await llm.ainvoke(chat_messages)
            text = resp.content or ""
        except Exception:
            text = "你好！我是大众点评 AI 小探 🍴 告诉我你想吃什么，我帮你找最合适的餐厅～"
        await add_message(conv_id, "assistant", text)

        # Analyze and update user profile
        try:
            profile_data = await analyze_conversation_for_profile(query, text)
            if any([
                profile_data.get("locations"),
                profile_data.get("cuisine_preferences"),
                profile_data.get("taste_preferences"),
                profile_data.get("dining_scenarios"),
                profile_data.get("budget_level"),
                profile_data.get("other_keywords"),
            ]):
                from .user_profile import update_user_profile
                await update_user_profile(conv_id, profile_data)
        except Exception as e:
            logger.warning(f"Failed to update user profile: {e}")

        return conv_id, text, []

    # build
    context = build_context(businesses)
    history = await get_history(conv_id)
    user_prompt = build_user_prompt(query, context, history, profile_text)

    await add_message(conv_id, "user", query)

    llm = get_llm()
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        resp = await llm.ainvoke(messages)
        text = resp.content or ""
    except Exception as e:
        text = f"抱歉，AI 服务暂时不可用: {e}"

    await add_message(conv_id, "assistant", text)

    # Analyze and update user profile
    try:
        profile_data = await analyze_conversation_for_profile(query, text)
        if any([
            profile_data.get("locations"),
            profile_data.get("cuisine_preferences"),
            profile_data.get("taste_preferences"),
            profile_data.get("dining_scenarios"),
            profile_data.get("budget_level"),
            profile_data.get("other_keywords"),
        ]):
            from .user_profile import update_user_profile
            await update_user_profile(conv_id, profile_data)
    except Exception as e:
        logger.warning(f"Failed to update user profile: {e}")

    recs = _build_recommendations(businesses)

    return conv_id, text, recs


# ═══════════════════════════════════════════════════════════════
# Business-side analysis (口碑分析)
# ═══════════════════════════════════════════════════════════════

async def _analyze_business_stream(
    query: str,
    conv_id: str,
    business_id: str,
) -> AsyncIterator[str]:
    """Business-side analysis pipeline (streaming).

    Steps:
    1. Fetch business info from OpenSearch
    2. Fetch reviews for this business
    3. Build analysis prompt
    4. Stream LLM response
    5. Store assistant response
    6. Yield empty recommendations + done event
    """
    # 1. Yield start event (with mode for frontend)
    yield _sse("start", {"conversation_id": conv_id, "mode": "business"})

    # 2. Store user message
    await add_message(conv_id, "user", query)

    # 3. Fetch business info
    business = _get_business_info(business_id)
    if not business:
        error_msg = f"抱歉，未找到该商家信息（ID: {business_id}）。请确认商家 ID 是否正确。"
        yield _sse("delta", {"content": error_msg})
        await add_message(conv_id, "assistant", error_msg)
        yield f"data: {{\"type\": \"recommendations\", \"items\": []}}\n\n"
        yield _sse("done", {"total_tokens": 0})
        return

    # 4. Fetch reviews
    reviews = _search_reviews(business_id, top_k=50)
    if not reviews:
        no_reviews_msg = (
            f"「{business.get('name', '该商家')}」目前还没有顾客评价。\n\n"
            "建议引导顾客在消费后留下评价，这样我就能帮你分析口碑啦～"
        )
        yield _sse("delta", {"content": no_reviews_msg})
        await add_message(conv_id, "assistant", no_reviews_msg)
        yield f"data: {{\"type\": \"recommendations\", \"items\": []}}\n\n"
        yield _sse("done", {"total_tokens": 0})
        return

    # 5. Build analysis prompt
    history = await get_history(conv_id)
    user_prompt = build_business_analysis_prompt(query, business, reviews, history)

    # 6. Stream LLM response
    llm = get_llm()
    full_response = ""

    try:
        messages = [
            {"role": "system", "content": BUSINESS_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                yield _sse("delta", {"content": chunk.content})

    except Exception as e:
        error_msg = f"抱歉，AI 服务暂时不可用，请稍后重试。({e})"
        full_response = error_msg
        yield _sse("delta", {"content": error_msg})

    # 7. Store assistant response
    await add_message(conv_id, "assistant", full_response)

    # 8. Yield empty recommendations + done
    yield f"data: {{\"type\": \"recommendations\", \"items\": []}}\n\n"
    yield _sse("done", {"total_tokens": len(full_response)})


async def _analyze_business_generate(
    query: str,
    conv_id: str,
    business_id: str,
) -> tuple[str, str, list[RecommendationItem]]:
    """Business-side analysis pipeline (non-streaming).

    Returns:
        (conversation_id, text, []) — recommendations is always empty for analysis.
    """
    await add_message(conv_id, "user", query)

    # Fetch business info
    business = _get_business_info(business_id)
    if not business:
        text = f"抱歉，未找到该商家信息（ID: {business_id}）。请确认商家 ID 是否正确。"
        await add_message(conv_id, "assistant", text)
        return conv_id, text, []

    # Fetch reviews
    reviews = _search_reviews(business_id, top_k=50)
    if not reviews:
        text = (
            f"「{business.get('name', '该商家')}」目前还没有顾客评价。\n\n"
            "建议引导顾客在消费后留下评价，这样我就能帮你分析口碑啦～"
        )
        await add_message(conv_id, "assistant", text)
        return conv_id, text, []

    # Build prompt
    history = await get_history(conv_id)
    user_prompt = build_business_analysis_prompt(query, business, reviews, history)

    # Invoke LLM
    llm = get_llm()
    try:
        messages = [
            {"role": "system", "content": BUSINESS_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        resp = await llm.ainvoke(messages)
        text = resp.content or ""
    except Exception as e:
        text = f"抱歉，AI 服务暂时不可用: {e}"

    await add_message(conv_id, "assistant", text)

    return conv_id, text, []


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _sse(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event line."""
    payload = json.dumps({"type": event_type, **data}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _build_recommendations(
    businesses: list[dict],
) -> list[RecommendationItem]:
    """Convert raw OpenSearch business hits to structured RecommendationItems.

    Args:
        businesses: Raw business dicts (must contain ``business_id``, ``name``,
            ``stars``, ``review_count``, ``categories``, ``address``, ``city``,
            and optionally ``_score``).

    Returns:
        List of ``RecommendationItem`` (up to 5), each with source reviews
        attached.
    """
    items: list[RecommendationItem] = []
    for biz in businesses[:5]:
        biz_id = biz.get("business_id", "")
        reviews = _search_reviews(biz_id, top_k=3)

        sources: list[SourceInfo] = []
        for r in reviews:
            sources.append(SourceInfo(
                user_name=f"用户{str(r.get('user_id', '匿名'))[:8]}",
                rating=float(r.get("stars", 0)),
                date=str(r.get("date", "")),
                text=str(r.get("text", ""))[:300],
                business_name=str(biz.get("name", "")),
            ))

        categories_raw = biz.get("categories", "")
        if isinstance(categories_raw, str):
            categories_list = [
                c.strip() for c in categories_raw.split(",") if c.strip()
            ]
        else:
            categories_list = (
                list(categories_raw) if categories_raw else []
            )

        items.append(RecommendationItem(
            business_id=biz_id,
            name=str(biz.get("name", "")),
            rating=float(biz.get("stars", 0)),
            review_count=int(biz.get("review_count", 0)),
            categories=categories_list[:8],
            address=str(biz.get("address", "")),
            city=str(biz.get("city", "")),
            reason="",
            sources=sources,
            score=float(biz.get("_score", 0)),
        ))

    return items
