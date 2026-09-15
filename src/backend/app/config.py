from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 1

    # bcrypt (4-31 is bcrypt's valid range; 15+ costs seconds per hash, so cap below that)
    bcrypt_rounds: int = Field(default=12, ge=4, le=14)

    # Ausführlichkeit des Logs in API und Worker (T-63). Nicht als Enum typisiert:
    # ein unbekannter Wert soll auf INFO zurückfallen und das sagen, nicht den
    # Start verhindern — die Begründung steht in app/logging_config.py.
    log_level: str = "INFO"

    # Kommagetrennte CORS-Origins (T-63). Der Default ist leer und meint „gar
    # keine": nginx liefert SPA und API unter derselben Origin aus
    # (`location /api/`), im ausgelieferten Setup kommt also kein Cross-Origin-
    # Zugriff vor. Vorher stand hier `["*"]` zusammen mit `allow_credentials` —
    # heute nicht ausnutzbar, weil das Token laut ADR-002 im Speicher liegt und
    # nicht als Cookie mitfährt, aber als Vorlage für den nächsten Endpoint falsch.
    cors_allow_origins: str = ""

    @property
    def cors_origins(self) -> list[str]:
        """Die Origins als Liste; leere Einträge fallen weg, damit ein
        Trennzeichen zu viel nicht als Origin "" durchkommt."""
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    # Swagger UI, ReDoc and /openapi.json publish the complete API surface, and
    # FastAPI serves them without authentication. Off unless a deployment opts
    # in, so the pilot cannot publish them by omission — the contract lives in
    # openapi.yaml (ADR-010), the served schema is only a development aid.
    expose_api_docs: bool = False

    def validate_secrets(self) -> None:
        """Fail-closed check on JWT_SECRET, deliberately outside pydantic.

        A pydantic validator would raise ValidationError, whose message embeds the
        raw settings source dict as `input_value` — that puts (truncated) parts of
        DATABASE_URL and OPENAI_API_KEY into the container log on every failed
        start. Raising a plain ValueError here keeps the message value-free.
        """
        if len(self.jwt_secret) < 32 or "changeme" in self.jwt_secret.lower():
            raise ValueError(
                "JWT_SECRET must be a strong random value of at least 32 characters. "
                "Generate one with: openssl rand -hex 32"
            )

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
settings.validate_secrets()
