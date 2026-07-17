"""Conversation history management — Redis-backed via base_config.

All functions are async and delegate to base_config.conversation, which uses
Redis for persistent, cross-process conversation storage.
"""

from __future__ import annotations

# Re-export async Redis-backed implementations from base_config
from base_config.conversation import (
    add_message,
    clear_conversation,
    conversation_count,
    get_history,
    get_or_create_conversation,
    get_recent_history,
)
