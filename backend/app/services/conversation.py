"""Conversation history management.

Provides an in-memory conversation store with helpers for multi-turn chat.
Replace with Redis or a database for production deployments.
"""

from __future__ import annotations

import uuid
from collections import deque

# ── In-memory store ───────────────────────────────────────
# Map: conversation_id → deque of {"role", "content"} dicts
_conversations: dict[str, deque[dict[str, str]]] = {}
MAX_HISTORY = 20  # max messages per conversation


def get_or_create_conversation(conversation_id: str | None = None) -> str:
    """Return an existing conversation id or create a new one.

    Args:
        conversation_id: If provided and exists, it is reused; otherwise a new
            12-char hex id is generated.

    Returns:
        A valid conversation id.
    """
    if conversation_id and conversation_id in _conversations:
        return conversation_id
    new_id = uuid.uuid4().hex[:12]
    _conversations[new_id] = deque(maxlen=MAX_HISTORY)
    return new_id


def add_message(conversation_id: str, role: str, content: str) -> None:
    """Append a message to the conversation history.

    Args:
        conversation_id: Target conversation.
        role: ``"user"`` or ``"assistant"``.
        content: Message body.
    """
    if conversation_id not in _conversations:
        _conversations[conversation_id] = deque(maxlen=MAX_HISTORY)
    _conversations[conversation_id].append({"role": role, "content": content})


def get_history(conversation_id: str) -> list[dict[str, str]]:
    """Return the full message history for a conversation.

    Args:
        conversation_id: Target conversation.

    Returns:
        List of ``{"role": ..., "content": ...}`` dicts, oldest first.
    """
    return list(_conversations.get(conversation_id, []))


def get_recent_history(
    conversation_id: str, n: int = 6
) -> list[dict[str, str]]:
    """Return the most recent *n* messages (default: last 3 exchanges).

    Args:
        conversation_id: Target conversation.
        n: Number of recent messages to return.

    Returns:
        Slice of the history list.
    """
    history = get_history(conversation_id)
    return history[-n:] if len(history) > n else history


def clear_conversation(conversation_id: str) -> None:
    """Delete a conversation and its history.

    Args:
        conversation_id: Conversation to remove.
    """
    _conversations.pop(conversation_id, None)


def conversation_count() -> int:
    """Return the number of active conversations (for monitoring)."""
    return len(_conversations)
