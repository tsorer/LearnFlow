"""Tests for the JWT_SECRET startup validator (app/config.py)."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings(**overrides: str) -> Settings:
    values = {
        "database_url": "postgresql://x",
        "jwt_secret": "a" * 32,
        "openai_api_key": "sk-test",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_jwt_secret_too_short_raises() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(jwt_secret="short")


def test_jwt_secret_containing_changeme_raises() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(jwt_secret="changeme_" + "a" * 30)


def test_jwt_secret_valid_does_not_raise() -> None:
    settings = _settings(jwt_secret="a" * 32)
    assert settings.jwt_secret == "a" * 32
