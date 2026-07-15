"""Services package — public API surface.

Import what callers need from here, or import directly from sub-modules::

    from app.services import get_llm
    from app.services.rag_service import rag_stream
"""

from app.services.llm_client import get_llm, reset_llm
from app.services.conversation import (
    add_message,
    clear_conversation,
    get_history,
    get_or_create_conversation,
    get_recent_history,
)
from app.services.prompts import (
    SYSTEM_PROMPT,
    CLARIFY_PROMPT,
    FALLBACK_MESSAGE,
    build_context,
    build_user_prompt,
    build_clarify_prompt,
)
from app.services.rag_service import rag_stream, rag_generate

__all__ = [
    # llm_client
    "get_llm",
    "reset_llm",
    # conversation
    "add_message",
    "clear_conversation",
    "get_history",
    "get_or_create_conversation",
    "get_recent_history",
    # prompts
    "SYSTEM_PROMPT",
    "CLARIFY_PROMPT",
    "FALLBACK_MESSAGE",
    "build_context",
    "build_user_prompt",
    "build_clarify_prompt",
    # rag
    "rag_stream",
    "rag_generate",
]
