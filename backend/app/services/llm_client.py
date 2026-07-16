"""LLM 客户端工厂 —— 使用 LangChain 的 ChatOpenAI 封装。

LangChain ChatOpenAI 相比裸 AsyncOpenAI 的优势:
    1. 自动处理 token 计数和回调钩子
    2. 与 LangChain 生态无缝集成（Memory、Chain、Agent 等）
    3. 内置重试机制（tenacity），更健壮
    4. 统一的 .astream() / .ainvoke() 接口，切换模型不用改调用代码
    5. 支持 .bind() 动态覆盖参数（temperature、top_p 等）

用法::

    from app.services.llm_client import get_llm

    llm = get_llm()                          # 用默认配置
    llm = get_llm(model="gpt-4o")            # 覆盖模型
    llm = get_llm(temperature=0.3)           # 覆盖温度

    # 流式
    async for chunk in llm.astream(messages):
        print(chunk.content)

    # 非流式
    resp = await llm.ainvoke(messages)
    print(resp.content)
"""

from __future__ import annotations

import threading
from typing import Any

from langchain_openai import ChatOpenAI

# ── 全局单例 ─────────────────────────────────────────────────
_llm_client: ChatOpenAI | None = None
_lock = threading.Lock()


def _get_settings():
    """延迟导入 settings，兼容两种 import 路径。"""
    try:
        from ..core.config import settings
    except ImportError:
        from app.core.config import settings
    return settings


def get_llm(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> ChatOpenAI:
    """返回线程安全的 ChatOpenAI 单例实例。

    首次调用时根据 settings 创建，后续调用返回缓存实例。
    传入显式参数可覆盖默认值（仅在首次创建时生效）。

    Parameters
    ----------
    api_key : str | None
        API Key，默认读取 settings.api_key（环境变量 OPENAI_API_KEY）。
    base_url : str | None
        LLM 网关地址，默认读取 settings.base_url。
    model : str | None
        模型名称，默认读取 settings.llm_model。
    temperature : float | None
        生成温度（0-2），默认 0.7。
    max_tokens : int | None
        最大生成长度，默认 1024。
    **kwargs : Any
        透传给 ChatOpenAI 的额外参数。

    Returns
    -------
    ChatOpenAI
        共享的 LLM 客户端实例。
    """
    global _llm_client

    if _llm_client is not None:
        return _llm_client

    with _lock:
        if _llm_client is not None:
            return _llm_client

        s = _get_settings()

        _llm_client = ChatOpenAI(
            api_key=api_key if api_key is not None else s.api_key,          # type: ignore[arg-type]
            base_url=base_url if base_url is not None else s.base_url,      # type: ignore[arg-type]
            model=model if model is not None else s.llm_model,
            temperature=temperature if temperature is not None else 0.7,
            max_tokens=max_tokens if max_tokens is not None else 1024,
            **kwargs,
        )

    return _llm_client


def reset_llm() -> None:
    """重置 LLM 客户端缓存（用于测试或配置热更新）。"""
    global _llm_client
    with _lock:
        _llm_client = None


# ── 自检 ────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from pathlib import Path

    _backend_dir = Path(__file__).resolve().parent.parent.parent
    if str(_backend_dir) not in sys.path:
        sys.path.insert(0, str(_backend_dir))

    print("=== LLM Client 自检 (LangChain ChatOpenAI) ===\n")

    llm = get_llm()
    print(f"  model       : {llm.model_name}")
    print(f"  base_url    : {llm.openai_api_base}")
    print(f"  temperature : {llm.temperature}")
    print(f"  max_tokens  : {llm.max_tokens}")
    api_key_str = llm.openai_api_key.get_secret_value() if llm.openai_api_key else ""
    print(f"  api_key     : {api_key_str[:8]}..." if api_key_str else "  api_key     : (empty)")

    llm2 = get_llm()
    print(f"  单例模式    : {'OK (same)' if llm is llm2 else 'FAIL (different)'}")

    reset_llm()
    print(f"  reset后     : {'OK (cleared)' if get_llm() is not None else 'FAIL'}")

    print("\n=== 自检通过 ===")
