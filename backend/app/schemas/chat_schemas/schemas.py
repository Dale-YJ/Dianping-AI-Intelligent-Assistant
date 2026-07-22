"""Request / response schemas for the chat API."""
from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户自然语言输入")
    conversation_id: str | None = Field(None, description="会话 ID，用于多轮对话")
    business_id: str | None = Field(None, description="商家端对话时传入，触发口碑分析模式（跳过 RAG 检索）")


# ── Response payloads ────────────────────────────────────

class SourceInfo(BaseModel):
    """A single evaluation source referenced in the recommendation."""
    user_name: str = ""
    rating: float = 0.0
    date: str = ""
    text: str = ""
    business_name: str = ""


class RecommendationItem(BaseModel):
    """One recommended business."""
    business_id: str = ""
    name: str = ""
    rating: float = 0.0
    review_count: int = 0
    categories: list[str] = []
    address: str = ""
    city: str = ""
    reason: str = ""                     # AI-generated recommendation reason
    sources: list[SourceInfo] = []       # cited reviews
    score: float = 0.0                   # retrieval relevance score


class ChatResponse(BaseModel):
    """Non-streaming fallback response."""
    conversation_id: str
    text: str
    recommendations: list[RecommendationItem] = []
    is_fallback: bool = False


class StreamStart(BaseModel):
    """First SSE event: metadata."""
    type: str = "start"
    conversation_id: str


class StreamDelta(BaseModel):
    """SSE event: text chunk."""
    type: str = "delta"
    content: str


class StreamRecommendations(BaseModel):
    """SSE event: parsed recommendations."""
    type: str = "recommendations"
    items: list[RecommendationItem]


class StreamDone(BaseModel):
    """SSE event: stream complete."""
    type: str = "done"
    total_tokens: int = 0


# ── Conversation list ────────────────────────────────────

class ConversationItem(BaseModel):
    """A single conversation in the list."""
    id: str
    title: str
    message_count: int
    updated_at: int  # unix timestamp


class ConversationListResponse(BaseModel):
    """Response for GET /api/chat/conversations."""
    conversations: list[ConversationItem]
