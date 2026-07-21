"""LLM client factory — provides a reusable ``get_llm()`` for the whole project.

Usage::

    from app.services.llm_client import get_llm

    llm = get_llm()                        # uses settings defaults
    llm = get_llm(model="gpt-4o")          # override model
    llm = get_llm(api_key="sk-...", base_url="https://...")

The returned client is an ``openai.AsyncOpenAI`` instance, suitable for both
streaming and non-streaming calls.
"""

import threading
from typing import Any
from langchain_openai import ChatOpenAI
from backend.app.core.config import settings

# ── Global singleton ───────────────────────────────────────
_llm_client: ChatOpenAI | None = None
_lock = threading.Lock()

def get_llm(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> ChatOpenAI:

    global _llm_client

    if _llm_client is not None:
        return _llm_client

    with _lock:
        if _llm_client is not None:
            return _llm_client


        resolved_api_key = api_key if api_key is not None else settings.api_key
        resolved_base_url = base_url if base_url is not None else settings.base_url
        resolved_model = model if model is not None else settings.llm_model

        _llm_client = ChatOpenAI(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            **kwargs,
        )
    return _llm_client

def reset_llm() -> None:
    """Reset the cached LLM client (useful for tests or config reloads)."""
    global _llm_client
    with _lock:
        _llm_client = None


# ── Self-test (run directly: python llm_client.py) ─────────
if __name__ == "__main__":

    print("=== LLM Client 自检 ===\n")
    llm = get_llm()

    res = llm.invoke("hello ,please introduce yourself,include your model name,base_url,")
    print(res.content)

    # singleton test
    llm2 = get_llm()
    print(f"  单例模式 : {'OK (same)' if llm is llm2 else 'FAIL (different)'}")

    # reset test
    reset_llm()
    print(f"  reset后  : {'OK (cleared)' if get_llm() is not None else 'FAIL'}")

    print("\n=== 自检通过 ===")
