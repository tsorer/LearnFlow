from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str  # postgresql://user:pass@host:5432/db

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8

    # LLM / Embeddings (via LiteLLM)
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    embed_model: str = "text-embedding-3-small"
    embed_dimensions: int = 1536
    litellm_base_url: str = ""
    litellm_api_version: str = ""
    litellm_api_key: str = ""

    # RAG defaults — overridden by config table at runtime
    similarity_threshold: float = 0.60
    min_retrieval_confidence: float = 0.55
    min_citation_coverage: float = 0.50
    self_check_band_low: float = 0.50   # self-check triggers between low and high
    self_check_band_high: float = 0.75
    top_k: int = 20
    top_n: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64

    @property
    def sqlalchemy_url(self) -> str:
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    @property
    def asyncpg_dsn(self) -> str:
        return self.database_url


settings = Settings()
