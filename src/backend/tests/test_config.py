"""Tests for the JWT_SECRET startup validator and the CORS origins (app/config.py)."""

import pytest
from pydantic import ValidationError

from app.config import Settings

DB_PASSWORD = "SuperSecretDbPw"
API_KEY = "sk-proj-REALKEY1234567890abcdefXYZ"


def _settings(**overrides: str) -> Settings:
    values = {
        "database_url": f"postgresql://learnflow:{DB_PASSWORD}@db:5432/learnflow",
        "jwt_secret": "a" * 32,
        "openai_api_key": API_KEY,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_jwt_secret_too_short_raises() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        _settings(jwt_secret="short").validate_secrets()


def test_jwt_secret_containing_changeme_raises() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        _settings(jwt_secret="changeme_" + "a" * 30).validate_secrets()


def test_jwt_secret_valid_does_not_raise() -> None:
    settings = _settings(jwt_secret="a" * 32)
    settings.validate_secrets()
    assert settings.jwt_secret == "a" * 32


def test_error_message_carries_no_secret_values() -> None:
    """The failed start is logged — the message must not leak the other secrets."""
    with pytest.raises(ValueError) as exc_info:
        _settings(jwt_secret="changeme_x").validate_secrets()

    message = str(exc_info.value)
    assert DB_PASSWORD not in message
    assert API_KEY not in message
    assert "changeme_x" not in message


def test_bcrypt_rounds_above_cap_rejected() -> None:
    """15+ costs seconds per hash — the cap keeps the login path responsive."""
    with pytest.raises(ValidationError, match="bcrypt_rounds"):
        _settings(bcrypt_rounds="15")


# ---- CORS-Origins (T-63) ----------------------------------------------------
#
# Vorher stand `allow_origins=["*"]` fest im Code. Was hier geprueft wird, ist die
# Uebersetzung der einen ENV-Zeile in die Liste, die `app/main.py` der Middleware
# gibt -- und vor allem der Default, der die Middleware gar nicht erst registriert.


def test_no_origins_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Der ausgelieferte Fall: nginx liefert SPA und API unter derselben Origin
    aus, ein Cross-Origin-Zugriff kommt nicht vor.

    `delenv` ist hier nicht Deko: `_settings()` reicht nur die drei Pflichtfelder
    durch, alle uebrigen fuellt pydantic-settings weiterhin aus der Umgebung.
    docker-compose.yml gibt der api ihr `env_file: .env` als echte
    Umgebungsvariablen mit -- ein Entwickler, der `CORS_ALLOW_ORIGINS` dort
    setzt (die .env.example nennt die Zeile), haette diesen Test rot gemacht,
    ohne dass am Code etwas falsch waere. Die Faelle darunter sind davon nicht
    betroffen: ein explizites Argument schlaegt die Umgebung.
    """
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    assert _settings().cors_origins == []


def test_single_origin() -> None:
    assert _settings(cors_allow_origins="http://localhost:5173").cors_origins == [
        "http://localhost:5173"
    ]


def test_several_origins_are_split_and_trimmed() -> None:
    settings = _settings(cors_allow_origins="http://a.invalid, https://b.invalid")

    assert settings.cors_origins == ["http://a.invalid", "https://b.invalid"]


def test_stray_separators_do_not_become_an_empty_origin() -> None:
    """Ein Trennzeichen zu viel darf keine Origin "" erzeugen -- die wuerde die
    Middleware als zu vergleichenden Wert fuehren, ohne je zu passen."""
    assert _settings(cors_allow_origins="http://a.invalid,,  ,").cors_origins == [
        "http://a.invalid"
    ]
