"""RAG service — orchestrates retrieval + LLM generation with streaming.

This module ties together the separated concerns:
- ``llm_client`` — LLM connection
- ``conversation`` — multi-turn history
- ``prompts`` — prompt engineering
- ``search_service`` — OpenSearch retrieval
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from ..core.config import settings
from ..schemas.schemas import RecommendationItem, SourceInfo
from .conversation import (
    add_message,
    get_history,
    get_or_create_conversation,
)
from .llm_client import get_llm
from .prompts import (
    FALLBACK_MESSAGE,
    SYSTEM_PROMPT,
    build_clarify_prompt,
    build_context,
    build_user_prompt,
)
from .search_service import search_businesses, search_reviews_for_business


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
    conv_id = get_or_create_conversation(conversation_id)

    # 1. yield start event
    yield _sse("start", {"conversation_id": conv_id})

    # 2. store user message
    add_message(conv_id, "user", query)

    # 3. search
    businesses = search_businesses(query)

    # 4. fallback if no results
    if not businesses:
        fallback_text = FALLBACK_MESSAGE.format(query=query)
        add_message(conv_id, "assistant", fallback_text)
        yield _sse("delta", {"content": fallback_text})
        yield f"data: {{\"type\": \"recommendations\", \"items\": []}}\n\n"
        yield _sse("done", {"total_tokens": 0})
        return

    # 5. build context & prompt
    context = build_context(businesses)
    history = get_history(conv_id)
    user_prompt = build_user_prompt(query, context, history)

    # 6. prepare structured recommendations
    recs = _build_recommendations(businesses)

    # 7. stream LLM response
    llm = get_llm()
    full_response = ""

    try:
        stream = await llm.chat.completions.create(
            model=getattr(llm, "_model_name", settings.llm_model),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_response += delta.content
                yield _sse("delta", {"content": delta.content})

    except Exception as e:
        error_msg = f"抱歉，AI 服务暂时不可用，请稍后重试。({e})"
        full_response = error_msg
        yield _sse("delta", {"content": error_msg})

    # 8. store assistant response
    add_message(conv_id, "assistant", full_response)

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
    conv_id = get_or_create_conversation(conversation_id)

    # search
    businesses = search_businesses(query)

    if not businesses:
        text = FALLBACK_MESSAGE.format(query=query)
        add_message(conv_id, "user", query)
        add_message(conv_id, "assistant", text)
        return conv_id, text, []

    # build
    context = build_context(businesses)
    history = get_history(conv_id)
    user_prompt = build_user_prompt(query, context, history)

    add_message(conv_id, "user", query)

    llm = get_llm()
    try:
        resp = await llm.chat.completions.create(
            model=getattr(llm, "_model_name", settings.llm_model),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        text = resp.choices[0].message.content or ""
    except Exception as e:
        text = f"抱歉，AI 服务暂时不可用: {e}"

    add_message(conv_id, "assistant", text)
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
        reviews = search_reviews_for_business(biz_id, top_k=3)

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
