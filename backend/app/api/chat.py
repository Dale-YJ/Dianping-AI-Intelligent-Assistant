"""Chat API — SSE streaming and non-streaming endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

try:
    from backend.app.schemas.chat_schemas.schemas import ChatRequest, ChatResponse
    from backend.app.services.chat_services.conversation import (
        clear_conversation,
        get_history,
        get_or_create_conversation,
    )
    from backend.app.services.chat_services.rag_service import (
        _build_recommendations,
        rag_generate,
        rag_stream,
    )
except ImportError:
    logger.warning(
        "Failed to import via 'backend.app.*' prefix, falling back to 'app.*'. "
        "Ensure base_config/ is on sys.path.",
        exc_info=True,
    )
    from app.schemas.chat_schemas.schemas import ChatRequest, ChatResponse  # type: ignore[no-redef]
    from app.services.chat_services.conversation import (  # type: ignore[no-redef]
        clear_conversation,
        get_history,
        get_or_create_conversation,
    )
    from app.services.chat_services.rag_service import (  # type: ignore[no-redef]
        _build_recommendations,
        rag_generate,
        rag_stream,
    )

router = APIRouter(prefix="/api/chat", tags=["chat"])


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
        rag_stream(req.message, req.conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/send", response_model=ChatResponse)
async def chat_send(req: ChatRequest):
    """Non-streaming fallback: returns the complete AI response at once."""
    conv_id, text, recs = await rag_generate(req.message, req.conversation_id)

    is_fallback = len(recs) == 0

    return ChatResponse(
        conversation_id=conv_id,
        text=text,
        recommendations=recs,
        is_fallback=is_fallback,
    )


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
