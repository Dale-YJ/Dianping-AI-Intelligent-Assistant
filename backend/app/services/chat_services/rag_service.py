"""RAG service — orchestrates retrieval + LLM generation with streaming.

This module ties together the separated concerns:
- ``llm_client`` — LLM connection
- ``conversation`` — multi-turn history
- ``prompts`` — prompt engineering
- ``search_service`` — OpenSearch retrieval
- ``query_rewriter`` — LLM-based query → concrete search conditions
- ``reranker`` — embedding-similarity re-ranking (bge-base-zh-v1.5)

Pipeline (updated):
    1. User query → rewrite_query() → concrete keywords + categories
    2. hybrid_search() with expanded candidate pool
    3. rerank() with bge-reranker-v2-m3 cross-encoder
    4. build_context() → LLM streaming → recommendations
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
    build_context,
    build_user_prompt,
)
from .query_rewriter import rewrite_query, build_search_query

# 统一使用 base_config 的 OpenSearch 客户端和检索接口
from opensearch_client import get_opensearch_client
from retrieve import hybrid_search
from reranker import rerank

logger = logging.getLogger(__name__)

BUSINESS_INDEX = "yelp_business"
REVIEW_INDEX = "yelp_review"

# Reranker settings
RERANK_CANDIDATE_MULTIPLIER = 4  # fetch top_k * N candidates, rerank, then trim
RERANK_MIN_POOL_SIZE = 15        # minimum candidates before reranking


def _search_businesses(query: str, top_k: int = 5, min_score: float = 0.3) -> list[dict]:
    """混合搜索商家，底层调 retrieve.hybrid_search，加 min_score 截断。"""
    results = hybrid_search(query, k=max(top_k * 2, 10), index_name=BUSINESS_INDEX)
    return [r for r in results if r.get("_score", 0) >= min_score][:top_k]


def _search_businesses_via_reviews(
    query: str,
    top_k: int = 10,
    min_score: float = 0.3,
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
    search_str = build_search_query(rewritten)

    logger.info(
        f"Query rewritten: is_specific={rewritten['is_specific']}, "
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

    biz_from_direct = hybrid_search(search_str, k=pool_size, index_name=BUSINESS_INDEX)
    biz_from_direct = [r for r in biz_from_direct if r.get("_score", 0) >= min_score]
    for b in biz_from_direct:
        b["_match_source"] = "business"

    biz_from_reviews = _search_businesses_via_reviews(search_str, top_k=pool_size)

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


# ═══════════════════════════════════════════════════════════════
# Main RAG stream
# ═══════════════════════════════════════════════════════════════

async def rag_stream(
    query: str,
    conversation_id: str | None = None,
) -> AsyncIterator[str]:
    """Execute the full RAG pipeline and yield SSE-formatted strings.

    Pipeline steps:
    1. Resolve / create conversation
    2. Store user message
    3. Search OpenSearch for matching businesses
    4. If no results → fallback with clarifying prompt
    5. Build RAG context + user prompt
    6. Stream LLM response token-by-token
    7. Store assistant response
    8. Yield structured recommendations
    9. Signal completion

    Yields:
        SSE event strings (``data: {...}\n\n``).
    """
    conv_id = await get_or_create_conversation(conversation_id)

    # 1. yield start event
    yield _sse("start", {"conversation_id": conv_id})

    # 2. store user message
    await add_message(conv_id, "user", query)

    # 3. search (with query rewriting + reranking)
    businesses = await _search_with_rewrite_and_rerank(query)

    # 4. no search results → let LLM chat naturally (handles greetings, small talk)
    if not businesses:
        history = await get_history(conv_id)
        chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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
        yield f"data: {{\"type\": \"recommendations\", \"items\": []}}\n\n"
        yield _sse("done", {"total_tokens": len(full_response)})
        return

    # 5. build context & prompt
    context = build_context(businesses)
    history = await get_history(conv_id)
    user_prompt = build_user_prompt(query, context, history)

    # 6. prepare structured recommendations
    recs = _build_recommendations(businesses)

    # 7. stream LLM response
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

    # 8. store assistant response
    await add_message(conv_id, "assistant", full_response)

    # 9. yield recommendations
    recs_json = json.dumps(
        [r.model_dump() for r in recs], ensure_ascii=False
    )
    yield f"data: {{\"type\": \"recommendations\", \"items\": {recs_json}}}\n\n"

    # 10. done
    yield _sse("done", {"total_tokens": len(full_response)})


# ═══════════════════════════════════════════════════════════════
# Non-streaming generation (fallback / debug)
# ═══════════════════════════════════════════════════════════════

async def rag_generate(
    query: str,
    conversation_id: str | None = None,
) -> tuple[str, str, list[RecommendationItem]]:
    """Non-streaming RAG: returns (conversation_id, text, recommendations).

    Useful for debugging or batch processing where streaming is unnecessary.
    """
    conv_id = await get_or_create_conversation(conversation_id)

    # search (with query rewriting + reranking)
    businesses = await _search_with_rewrite_and_rerank(query)

    if not businesses:
        history = await get_history(conv_id)
        chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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
        return conv_id, text, []

    # build
    context = build_context(businesses)
    history = await get_history(conv_id)
    user_prompt = build_user_prompt(query, context, history)

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
    recs = _build_recommendations(businesses)

    return conv_id, text, recs


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
