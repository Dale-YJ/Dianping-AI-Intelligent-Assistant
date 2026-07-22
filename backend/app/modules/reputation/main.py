"""商家口碑分析模块入口

FastAPI application entry point for reputation analysis module.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    # Test LLM connection
    try:
        from app.services.llm_client import get_llm
        llm = get_llm()
        model_name = getattr(llm, "model_name", "unknown")
        print(f"  LLM ready: {model_name}")
    except Exception as e:
        print(f"  LLM not ready: {e}")

    # Test data loading
    try:
        from base_config.opensearch_client import get_opensearch_client
        client = get_opensearch_client()
        count = client.count(index=settings.business_index)["count"]
        print(f"  Data loaded: {count} businesses")
    except Exception as e:
        print(f"  Data loading check failed: {e}")

    yield


app = FastAPI(
    title="商家口碑分析模块",
    description="关键特征词提取 + 评价情感分析 + 差评归因 + 经营建议",
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
from app.api.reputation import router as reputation_router
app.include_router(reputation_router)


@app.get("/")
async def root():
    """Redirect to API docs."""
    return RedirectResponse(url="/docs")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "商家口碑分析模块"}