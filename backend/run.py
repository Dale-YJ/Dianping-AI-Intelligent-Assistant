"""Backend startup script.

Usage:
    cd backend
    python run.py

Or from project root:
    python backend/run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend/ is on the Python path
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"🚀 大众点评 AI 智能助手 — 后端启动中...")
    print(f"   OpenSearch: {settings.opensearch_host}:{settings.opensearch_port}")
    print(f"   LLM: {settings.base_url} / {settings.llm_model}")
    print(f"   监听: http://{settings.host}:{settings.port}")
    print(f"   API 文档: http://localhost:{settings.port}/docs")

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )
