# config.py
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（config.py 所在的目录）
PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT.parent / ".env", extra="ignore")

    # LLM
    api_key: str = Field(default="", alias="OPENAI_API_KEY")
    base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    llm_model: str = Field(default="", alias="LLM_MODEL")

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_user: str = "admin"
    opensearch_password: str
    opensearch_use_ssl: bool = True
    opensearch_index: str = "rag_kb_v1"

    # models relative path
    embedding_model_path: str = "../models/bge-base-zh-v1.5"
    rerank_model_path: str = "../models/bge-reranker-v2-m3"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_max_connections: int = 10

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # models absolute path
    @property
    def embedding_model_dir(self) -> str:
        p = Path(self.embedding_model_path)
        if p.is_absolute():
            return str(p)
        return str((PROJECT_ROOT / p).resolve())

    @property
    def rerank_model_dir(self) -> str:
        p = Path(self.rerank_model_path)
        if p.is_absolute():
            return str(p)
        return str((PROJECT_ROOT / p).resolve())


settings = Settings()