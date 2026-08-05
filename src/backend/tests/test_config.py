"""Tests for the JWT_SECRET startup validator (app/config.py)."""

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
