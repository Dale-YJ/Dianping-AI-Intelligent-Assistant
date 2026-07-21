"""FastAPI application entry point — unified for all modules."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    # Ensure user_review index exists
    try:
        from app.services.analysis_services.review_service import ensure_user_review_index
        ensure_user_review_index()
        print("  User review index ready")
    except Exception as e:
        print(f"  User review index check failed: {e}")

    # Test LLM connection
    try:
        from app.services.llm_client import get_llm
        llm = get_llm()
        model_name = getattr(llm, "model_name", "unknown")
        print(f"  LLM ready: {model_name}")
    except Exception as e:
        print(f"  LLM not ready: {e}")

    # Test data loading (C module)
    try:
        from app.services.analysis_services.retrieval import get_all_businesses
        businesses = get_all_businesses()
        print(f"  Data loaded: {len(businesses)} businesses")
    except Exception as e:
        print(f"  Data loading failed: {e}")

    yield


app = FastAPI(
    title="大众点评 AI 智能助手",
    description="基于 RAG + DeepSeek 的智能探店与口碑分析平台",
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

from app.core.config import settings, PROJECT_ROOT

# ── Static files ────────────────────────────────────────
from pathlib import Path
from fastapi.staticfiles import StaticFiles

static_dir = PROJECT_ROOT / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Routers ──────────────────────────────────────────────
from app.api.analysis import router as analysis_router
app.include_router(analysis_router)


@app.get("/")
async def root():
    """Redirect to API docs."""
    return RedirectResponse(url="/docs")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "大众点评 AI 智能助手"}