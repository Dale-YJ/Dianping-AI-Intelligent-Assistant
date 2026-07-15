"""LLM client factory — provides a reusable ``get_llm()`` for the whole project.

Usage::

    from app.services.llm_client import get_llm

    llm = get_llm()                        # uses settings defaults
    llm = get_llm(model="gpt-4o")          # override model
    llm = get_llm(api_key="sk-...", base_url="https://...")

The returned client is an ``openai.AsyncOpenAI`` instance, suitable for both
streaming and non-streaming calls.
"""

from __future__ import annotations

import threading
from typing import Any

from openai import AsyncOpenAI

# ── Global singleton ───────────────────────────────────────
_llm_client: AsyncOpenAI | None = None
_lock = threading.Lock()


def _get_settings():
    """Lazy-import settings so the module can also run standalone."""
    from app.core.config import settings
    return settings


def get_llm(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> AsyncOpenAI:
    """Return a thread-safe singleton ``AsyncOpenAI`` client.

    On first call the client is created from ``settings``; subsequent calls
    return the cached instance.  Pass explicit arguments to override defaults
    (the override only takes effect on the *first* call — afterwards the
    singleton is locked).

    Parameters
    ----------
    api_key:
        API key forwarded to OpenAI-compatible providers.
        Defaults to ``settings.api_key``.
    base_url:
        Base URL of the LLM gateway.
        Defaults to ``settings.base_url``.
    model:
        Convenience parameter stored on the returned client as
        ``client._model_name`` so callers can read it back.
        Defaults to ``settings.llm_model``.
    **kwargs:
        Extra keyword arguments passed through to ``AsyncOpenAI.__init__``.

    Returns
    -------
    AsyncOpenAI
        The shared LLM client instance.
    """
    global _llm_client

    if _llm_client is not None:
        return _llm_client

    with _lock:
        if _llm_client is not None:
            return _llm_client

        settings = _get_settings()

        resolved_api_key = api_key if api_key is not None else settings.api_key
        resolved_base_url = base_url if base_url is not None else settings.base_url

        _llm_client = AsyncOpenAI(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            **kwargs,
        )
        # Attach model name for convenience
        _llm_client._model_name = model if model is not None else settings.llm_model  # type: ignore[attr-defined]

    return _llm_client


def reset_llm() -> None:
    """Reset the cached LLM client (useful for tests or config reloads)."""
    global _llm_client
    with _lock:
        _llm_client = None


# ── Self-test (run directly: python llm_client.py) ─────────
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Ensure backend/ is on sys.path so `app.core.config` can be resolved
    _backend_dir = Path(__file__).resolve().parent.parent.parent
    if str(_backend_dir) not in sys.path:
        sys.path.insert(0, str(_backend_dir))

    print("=== LLM Client 自检 ===\n")

    llm = get_llm()
    model = getattr(llm, "_model_name", "unknown")
    print(f"  base_url : {llm.base_url}")
    print(f"  model    : {model}")
    print(f"  api_key  : {llm.api_key[:8]}...{llm.api_key[-4:] if llm.api_key else '(empty)'}")

    # singleton test
    llm2 = get_llm()
    print(f"  单例模式 : {'OK (same)' if llm is llm2 else 'FAIL (different)'}")

    # reset test
    reset_llm()
    print(f"  reset后  : {'OK (cleared)' if get_llm() is not None else 'FAIL'}")

    print("\n=== 自检通过 ===")
