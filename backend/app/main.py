"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    # Pre-load embedding model on startup (avoid lazy-init delay on first request)
    from app.services.search_service import _get_embedding_model as _preload_embedding
    _preload_embedding()
    yield


app = FastAPI(
    title="大众点评 AI 智能助手",
    description="对话式探店推荐 API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
from app.api.chat import router as chat_router

app.include_router(chat_router)


@app.get("/")
async def root():
    """Redirect to API docs."""
    return RedirectResponse(url="/docs")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "大众点评 AI 智能助手"}
