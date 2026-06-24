from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 1

    # bcrypt
    bcrypt_rounds: int = 12

    @model_validator(mode="after")
    def check_jwt_secret(self) -> "Settings":
        if len(self.jwt_secret) < 32 or "changeme" in self.jwt_secret.lower():
            raise ValueError(
                "JWT_SECRET must be a strong random value of at least 32 characters. "
                "Generate one with: openssl rand -hex 32"
            )
        return self

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
