"""Application configuration — inherits from base_config and adds backend-specific settings."""
from pathlib import Path
import sys

# Add base_config to path
BASE_CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "base_config"
if BASE_CONFIG_ROOT not in sys.path:
    sys.path.insert(0, str(BASE_CONFIG_ROOT))

from config import Settings as BaseSettings

# Project root (backend/ directory)
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent



class Settings(BaseSettings):
    """Backend settings, inherits from base_config and adds backend-specific configurations."""

    # ── Backend-specific OpenSearch indexes ───────────────
    business_index: str = "yelp_business"
    review_index: str = "yelp_review"

    # ── RAG parameters ─────────────────────────────────────
    top_k: int = 5                    # number of businesses to retrieve
    similarity_threshold: float = 0.3  # min score for valid results
    max_context_chars: int = 3000     # max chars of review context

    # ── Server settings ────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


# Create singleton instance
settings = Settings()

# Export PROJECT_ROOT for compatibility
PROJECT_ROOT = BACKEND_ROOT.parent