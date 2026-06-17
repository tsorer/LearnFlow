from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

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

    @property
    def sqlalchemy_url(self) -> str:
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    @property
    def asyncpg_dsn(self) -> str:
        return self.database_url


settings = Settings()  # type: ignore[call-arg]
