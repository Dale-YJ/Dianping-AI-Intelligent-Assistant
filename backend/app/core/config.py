"""Application configuration — reuses base_config settings with backend-specific overrides."""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (backend/ directory)
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────
    api_key: str = Field(default="", alias="OPENAI_API_KEY")
    base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    llm_model: str = Field(default="", alias="LLM_MODEL")

    # ── OpenSearch ───────────────────────────────────────
    opensearch_host: str
    opensearch_port: int
    opensearch_user: str
    opensearch_password:str
    opensearch_use_ssl: bool = True

    #索引
    business_index: str = "yelp_business"
    review_index: str = "yelp_review"
    tip_index: str = "yelp_tip"
    user_index: str = "yelp_user"
    checkin_index: str = "yelp_checkin"

    # ── Embedding ────────────────────────────────────────
    embedding_model_path: str = "models/all-MiniLM-L6-v2"

    # ── RAG ──────────────────────────────────────────────
    top_k: int = 5                    # number of businesses to retrieve
    similarity_threshold: float = 0.3  # min score for valid results
    max_context_chars: int = 3000     # max chars of review context

    # ── Server ───────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def embedding_model_dir(self) -> str:
        p = Path(self.embedding_model_path)
        if p.is_absolute():
            return str(p)
        return str((PROJECT_ROOT / p).resolve())


settings = Settings()
