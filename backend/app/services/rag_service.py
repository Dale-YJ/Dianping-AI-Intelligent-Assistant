"""RAG service — orchestrates retrieval + LLM generation with streaming."""
from __future__ import annotations

import json
import re
import uuid
from collections import deque
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.schemas import RecommendationItem, SourceInfo
from app.services.search_service import search_businesses, search_reviews_for_business

# ── Conversation store (in-memory; replace with Redis for production) ──
# Each conversation keeps up to 20 messages (user/assistant pairs)
_conversations: dict[str, deque[dict[str, str]]] = {}
MAX_HISTORY = 20


# ── LLM client ───────────────────────────────────────────

_llm_client: AsyncOpenAI | None = None


def _get_llm() -> AsyncOpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )
    return _llm_client


# ── Conversation helpers ─────────────────────────────────

def get_or_create_conversation(conversation_id: str | None = None) -> str:
    """Return existing or new conversation id."""
    if conversation_id and conversation_id in _conversations:
        return conversation_id
    new_id = uuid.uuid4().hex[:12]
    _conversations[new_id] = deque(maxlen=MAX_HISTORY)
    return new_id


def add_message(conversation_id: str, role: str, content: str) -> None:
    if conversation_id not in _conversations:
        _conversations[conversation_id] = deque(maxlen=MAX_HISTORY)
    _conversations[conversation_id].append({"role": role, "content": content})


def get_history(conversation_id: str) -> list[dict[str, str]]:
    return list(_conversations.get(conversation_id, []))


def clear_conversation(conversation_id: str) -> None:
    _conversations.pop(conversation_id, None)


# ── Prompt builders ──────────────────────────────────────

_SYSTEM_PROMPT = """你是一个专业的美食探店助手，名叫"大众点评 AI 小探"。你的任务是基于真实的商家和评价数据，为用户推荐合适的餐厅。

## 你的能力
- 根据用户需求（菜系、场景、预算、口味偏好等），从检索到的商家中推荐最匹配的
- 每条推荐必须附带推荐理由，理由要具体、有说服力，引用真实评价中的信息
- 如果检索结果不够匹配，诚实告知用户，并给出替代建议

## 输出格式
对于每条推荐，请使用以下格式：

**推荐商家：{商家名称}**
- ⭐ 评分：{评分} | 📍 地址：{地址}
- 🏷️ 类别：{类别标签}
- 💬 推荐理由：{具体理由，引用评价内容}
- 📝 参考评价：[来源引用]

最后用 1-2 句话总结推荐。

## 重要规则
1. 只推荐检索结果中存在的商家，绝不编造
2. 推荐理由必须来源于检索到的评价内容
3. 如果检索结果为空或不相关，诚实告知并建议用户调整搜索条件
4. 回复简洁、口语化，像朋友推荐一样自然"""

_FALLBACK_MESSAGE = """抱歉，我在当前数据中暂时没有找到与「{query}」完全匹配的商家。😔

💡 **你可以试试：**
- 换个关键词，比如具体的菜系名（川菜、日料、火锅…）
- 试试场景化描述，比如"适合约会的餐厅""安静的咖啡馆"
- 扩大范围，比如"附近有什么好吃的"

我还在不断学习中，感谢你的理解！"""


def _build_context(businesses: list[dict]) -> str:
    """Build RAG context from retrieved businesses + their reviews."""
    parts: list[str] = []
    for i, biz in enumerate(businesses, 1):
        name = biz.get("name", "未知商家")
        stars = biz.get("stars", "N/A")
        city = biz.get("city", "")
        address = biz.get("address", "")
        categories = biz.get("categories", "")
        review_count = biz.get("review_count", 0)

        parts.append(
            f"[{i}] {name} | ⭐{stars} | 📍{address}, {city}\n"
            f"    类别: {categories} | 评价数: {review_count}"
        )

        # fetch top reviews
        biz_id = biz.get("business_id", "")
        if biz_id:
            reviews = search_reviews_for_business(biz_id, top_k=3)
            if reviews:
                parts.append("    精选评价:")
                for r in reviews:
                    text = r.get("text", "")
                    # truncate long reviews
                    if len(text) > 200:
                        text = text[:200] + "..."
                    parts.append(f"      - {r.get('stars', '?')}★ | {text}")

    return "\n".join(parts)


def _build_user_prompt(query: str, context: str, history: list[dict[str, str]]) -> str:
    """Build the final user prompt with context and history."""
    history_text = ""
    if history:
        recent = history[-6:]  # last 3 exchanges
        history_text = "## 对话历史\n" + "\n".join(
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
            for m in recent
        ) + "\n\n"

    return (
        f"{history_text}"
        f"## 检索到的商家数据\n{context}\n\n"
        f"## 用户问题\n{query}\n\n"
        f"请根据上面的检索数据为用户推荐最合适的商家。如果数据不足以回答用户问题，请诚实告知。"
    )


# ── Main RAG stream ──────────────────────────────────────

async def rag_stream(
    query: str,
    conversation_id: str | None = None,
) -> AsyncIterator[str]:
    """Execute RAG pipeline and yield SSE-formatted strings."""
    conv_id = get_or_create_conversation(conversation_id)

    # 1. yield start event
    yield _sse("start", {"conversation_id": conv_id})

    # 2. store user message
    add_message(conv_id, "user", query)

    # 3. search
    businesses = search_businesses(query)

    # 4. fallback if no good results
    if not businesses:
        fallback_text = _FALLBACK_MESSAGE.format(query=query)
        add_message(conv_id, "assistant", fallback_text)
        yield _sse("delta", {"content": fallback_text})
        recommendations_json = json.dumps([], ensure_ascii=False)
        yield f"data: {{\"type\": \"recommendations\", \"items\": []}}\n\n"
        yield _sse("done", {"total_tokens": 0})
        return

    # 5. build context & prompt
    context = _build_context(businesses)
    history = get_history(conv_id)
    user_prompt = _build_user_prompt(query, context, history)

    # 6. prepare recommendations data (filled in after LLM response)
    recs = _build_recommendations(businesses)

    # 7. stream LLM response
    llm = _get_llm()
    full_response = ""

    try:
        stream = await llm.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
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


# ── Helpers ──────────────────────────────────────────────

def _sse(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event line."""
    payload = json.dumps({"type": event_type, **data}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _build_recommendations(businesses: list[dict]) -> list[RecommendationItem]:
    """Convert search results to RecommendationItem list with source reviews."""
    items: list[RecommendationItem] = []
    for biz in businesses[:5]:
        biz_id = biz.get("business_id", "")
        reviews = search_reviews_for_business(biz_id, top_k=3)

        sources: list[SourceInfo] = []
        for r in reviews:
            sources.append(SourceInfo(
                user_name=f"用户{r.get('user_id', '匿名')[:8]}",
                rating=float(r.get("stars", 0)),
                date=str(r.get("date", "")),
                text=str(r.get("text", ""))[:300],
                business_name=str(biz.get("name", "")),
            ))

        categories_raw = biz.get("categories", "")
        if isinstance(categories_raw, str):
            categories_list = [c.strip() for c in categories_raw.split(",") if c.strip()]
        else:
            categories_list = list(categories_raw) if categories_raw else []

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
