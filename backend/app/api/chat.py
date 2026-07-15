"""Chat API — SSE streaming endpoint for conversational store exploration."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import (
    rag_stream,
    get_or_create_conversation,
    clear_conversation,
    get_history,
    _build_recommendations,
)
from app.services.search_service import search_businesses

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """Main endpoint: sends user message, returns SSE stream with AI response.

    Event types:
      - ``start``     → conversation metadata
      - ``delta``     → incremental LLM token
      - ``recommendations`` → structured recommendation cards
      - ``done``      → stream complete
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
    """Non-streaming fallback: returns complete response at once."""
    conv_id = get_or_create_conversation(req.conversation_id)

    # search
    businesses = search_businesses(req.message)

    if not businesses:
        from app.services.rag_service import _FALLBACK_MESSAGE
        text = _FALLBACK_MESSAGE.format(query=req.message)
        return ChatResponse(
            conversation_id=conv_id,
            text=text,
            recommendations=[],
            is_fallback=True,
        )

    recs = _build_recommendations(businesses)

    # simple non-streaming generation (for debugging / fallback)
    from app.services.rag_service import (
        _get_llm,
        _build_context,
        _build_user_prompt,
        get_history,
        add_message,
        _SYSTEM_PROMPT,
    )

    context = _build_context(businesses)
    history = get_history(conv_id)
    user_prompt = _build_user_prompt(req.message, context, history)

    add_message(conv_id, "user", req.message)

    llm = _get_llm()
    try:
        resp = await llm.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        text = resp.choices[0].message.content or ""
    except Exception as e:
        text = f"抱歉，AI 服务暂时不可用: {e}"

    add_message(conv_id, "assistant", text)

    return ChatResponse(
        conversation_id=conv_id,
        text=text,
        recommendations=recs,
    )


@router.get("/history/{conversation_id}")
async def conversation_history(conversation_id: str):
    """Get message history for a conversation."""
    history = get_history(conversation_id)
    return {"conversation_id": conversation_id, "messages": history}


@router.delete("/history/{conversation_id}")
async def clear_chat_history(conversation_id: str):
    """Clear a conversation's history."""
    clear_conversation(conversation_id)
    return {"status": "ok", "message": "Conversation cleared"}
