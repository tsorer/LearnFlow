"""T-63: die gemeinsamen Provider-Argumente der vier LiteLLM-Call-Sites.

Die Weiterreichung selbst prüfen `test_generation.py`, `test_embedding.py`,
`test_quiz_service.py` und `test_self_check.py` weiterhin je an ihrem eigenen
Aufruf — dass ein `api_base` also wirklich bei `litellm` ankommt, steht dort.
Hier steht nur, was `provider_args` aus den Settings macht, und zwar an der
einen Stelle, an der es seit T-63 entschieden wird.
"""

import pytest

from app.config import settings
from app.services.llm import provider_args


def test_empty_settings_become_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """"" ist für LiteLLM nicht None und würde als api_base den OpenAI-Direct-Pfad brechen."""
    monkeypatch.setattr(settings, "litellm_base_url", "")
    monkeypatch.setattr(settings, "litellm_api_version", "")

    args = provider_args()

    assert args["api_base"] is None
    assert args["api_version"] is None


def test_endpoint_is_passed_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Der Azure-Fall (ADR-004): gesetzte Werte gehen unverändert mit."""
    monkeypatch.setattr(settings, "litellm_base_url", "https://eu.example.invalid")
    monkeypatch.setattr(settings, "litellm_api_version", "2024-02-01")

    args = provider_args()

    assert args["api_base"] == "https://eu.example.invalid"
    assert args["api_version"] == "2024-02-01"


def test_gateway_key_wins_over_the_direct_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "litellm_api_key", "gateway-key")
    monkeypatch.setattr(settings, "openai_api_key", "sk-direct")

    assert provider_args()["api_key"] == "gateway-key"


def test_direct_key_is_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """MVP-Pfad: ohne Gateway-Schlüssel authentifiziert der OpenAI-Direct-Schlüssel."""
    monkeypatch.setattr(settings, "litellm_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "sk-direct")

    assert provider_args()["api_key"] == "sk-direct"


def test_settings_are_read_per_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nicht beim Import eingefroren — sonst griffe ein Endpunktwechsel erst nach
    einem Neustart, und die Call-Sites kämen nie an den geänderten Wert."""
    monkeypatch.setattr(settings, "litellm_base_url", "https://first.example.invalid")
    assert provider_args()["api_base"] == "https://first.example.invalid"

    monkeypatch.setattr(settings, "litellm_base_url", "https://second.example.invalid")
    assert provider_args()["api_base"] == "https://second.example.invalid"


def test_no_other_arguments_leak_in() -> None:
    """Modell, Timeout und num_retries bleiben bewusst bei den Call-Sites: sie
    unterscheiden sich fachlich je Aufruf, und `eval/profiles.py` überschreibt
    genau diese Modulkonstanten."""
    assert set(provider_args()) == {"api_base", "api_version", "api_key"}
