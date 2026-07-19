# config.py
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    # LLM
    api_key: str = Field(default="", alias="OPENAI_API_KEY")
    base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    llm_model: str = Field(default="", alias="OPENAI_LLM_MODEL")


    # OpenSearch
    opensearch_host: str=Field(default="", alias="OPENSEARCH_HOST")
    opensearch_port: int=Field(default=9200, alias="OPENSEARCH_PORT")
    opensearch_user: str=Field(default="", alias="OPENSEARCH_USER")
    opensearch_password: str=Field(default="", alias="OPENSEARCH_PASSWORD")
    opensearch_use_ssl: bool=Field(default=False, alias="OPENSEARCH_USE_SSL")

    # models relative path

    embedding_model_path: str = "models/bge-base-zh-v1.5"
    rerank_model_path: str = "models/bge-reranker-v2-m3"
    vector_dim: int = 768


    # Redis
    redis_host: str = Field(default="", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_max_connections: int =Field(default=0, alias="REDIS_MAX_CONNECTIONS")

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


    # models absolute path

    @property
    def embedding_model_dir(self) -> str:
        p = Path(self.embedding_model_path)
        print(p)
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

