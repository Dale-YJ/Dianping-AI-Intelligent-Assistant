"""Chat API — SSE streaming and non-streaming endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

try:
    from backend.app.schemas.chat_schemas.schemas import (
        ChatRequest,
        ChatResponse,
        ConversationItem,
        ConversationListResponse,
    )
    from backend.app.services.chat_services.conversation import (
        clear_conversation,
        get_history,
        get_or_create_conversation,
        list_conversations,
    )
    from backend.app.services.chat_services.rag_service import (
        _build_recommendations,
        rag_generate,
        rag_stream,
    )
    from backend.app.services.chat_services.user_profile import (
        get_user_profile,
        clear_user_profile,
    )
except ImportError:
    logger.warning(
        "Failed to import via 'backend.app.*' prefix, falling back to 'app.*'. "
        "Ensure base_config/ is on sys.path.",
        exc_info=True,
    )
    from app.schemas.chat_schemas.schemas import (  # type: ignore[no-redef]
        ChatRequest,
        ChatResponse,
        ConversationItem,
        ConversationListResponse,
    )
    from app.services.chat_services.conversation import (  # type: ignore[no-redef]
        clear_conversation,
        get_history,
        get_or_create_conversation,
        list_conversations,
    )
    from app.services.chat_services.rag_service import (  # type: ignore[no-redef]
        _build_recommendations,
        rag_generate,
        rag_stream,
    )
    from app.services.chat_services.user_profile import (  # type: ignore[no-redef]
        get_user_profile,
        clear_user_profile,
    )

router = APIRouter(prefix="/api/chat", tags=["chat"])

#流式输出
@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """Main SSE streaming endpoint.

    Event types emitted:
      - ``start``           → conversation metadata
      - ``delta``           → incremental LLM token
      - ``recommendations`` → structured recommendation cards
      - ``done``            → stream complete
    """
    return StreamingResponse(
        rag_stream(req.message, req.conversation_id, req.business_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

#一次性返回
@router.post("/send", response_model=ChatResponse)
async def chat_send(req: ChatRequest):
    """Non-streaming fallback: returns the complete AI response at once."""
    conv_id, text, recs = await rag_generate(req.message, req.conversation_id, req.business_id)

    is_fallback = len(recs) == 0

    return ChatResponse(
        conversation_id=conv_id,
        text=text,
        recommendations=recs,
        is_fallback=is_fallback,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def conversation_list():
    """List all conversations with metadata."""
    conversations = await list_conversations()
    return {"conversations": conversations}


@router.get("/history/{conversation_id}")
async def conversation_history(conversation_id: str):
    """Get message history for a conversation."""
    history = await get_history(conversation_id)
    return {"conversation_id": conversation_id, "messages": history}


@router.delete("/history/{conversation_id}")
async def clear_chat_history(conversation_id: str):
    """Clear a conversation's history."""
    await clear_conversation(conversation_id)
    return {"status": "ok", "message": "Conversation cleared"}


@router.get("/profile/{conversation_id}")
async def get_profile(conversation_id: str):
    """Get user profile for a conversation.

    Returns the user profile including:
    - locations: Mentioned locations/cities
    - cuisine_preferences: Preferred cuisine types
    - taste_preferences: Taste preferences
    - dining_scenarios: Dining scenarios
    - budget_level: Budget preference
    - other_keywords: Other keywords
    """
    profile = await get_user_profile(conversation_id)
    return {
        "conversation_id": conversation_id,
        "profile": profile.to_dict(),
    }


@router.delete("/profile/{conversation_id}")
async def clear_profile(conversation_id: str):
    """Clear user profile for a conversation."""
    await clear_user_profile(conversation_id)
    return {"status": "ok", "message": "Profile cleared"}


# ── Quick Tags ──────────────────────────────────────────────

QUICK_TAGS = [
    {"id": "sichuan", "label": "川菜推荐", "icon": "🌶️", "prompt": "推荐好吃的川菜馆"},
    {"id": "hotpot", "label": "火锅", "icon": "🍲", "prompt": "附近有什么好吃的火锅店？"},
    {"id": "japanese", "label": "日料", "icon": "🍣", "prompt": "推荐一家正宗的日料店"},
    {"id": "korean", "label": "韩式料理", "icon": "🥩", "prompt": "推荐好吃的韩式烤肉"},
    {"id": "canton", "label": "粤菜", "icon": "🥟", "prompt": "推荐地道的粤菜馆"},
    {"id": "western", "label": "西餐", "icon": "🍝", "prompt": "推荐一家不错的西餐厅"},
    {"id": "bbq", "label": "烧烤", "icon": "🍖", "prompt": "推荐好吃的烧烤店"},
    {"id": "seafood", "label": "海鲜", "icon": "🦞", "prompt": "推荐新鲜的海鲜餐厅"},
    {"id": "date", "label": "约会餐厅", "icon": "💑", "prompt": "适合约会的浪漫餐厅"},
    {"id": "family", "label": "家庭聚餐", "icon": "👨‍👩‍👧‍👦", "prompt": "适合家庭聚餐的餐厅"},
    {"id": "business", "label": "商务宴请", "icon": "🍽️", "prompt": "适合商务宴请的高档餐厅"},
    {"id": "friends", "label": "朋友聚会", "icon": "🎉", "prompt": "适合朋友聚会的热闹餐厅"},
    {"id": "quiet", "label": "安静办公", "icon": "💻", "prompt": "适合安静办公的咖啡馆"},
    {"id": "dessert", "label": "甜品咖啡", "icon": "🍰", "prompt": "推荐好吃的甜品店或咖啡馆"},
    {"id": "vegetarian", "label": "素食", "icon": "🥬", "prompt": "推荐好吃的素食餐厅"},
    {"id": "budget", "label": "经济实惠", "icon": "💰", "prompt": "推荐性价比高的平价美食"},
]


@router.get("/quick-tags")
async def chat_quick_tags():
    """Return quick-prompt tags with icons for the chat UI.

    Each tag contains:
      - id: unique identifier
      - label: display name
      - icon: emoji icon
      - prompt: pre-filled message when user clicks the tag
    """
    return {"tags": QUICK_TAGS}
