"""Wohin ein LiteLLM-Aufruf geht — an einer Stelle für alle vier Call-Sites (T-63).

Die Maintainability-NFA verlangt „LLM-Provider wechselbar durch Konfiguration —
kein Code-Change (LiteLLM-Abstraktion)", und ADR-004 macht den Wechsel von OpenAI
Direct auf Azure OpenAI EU zur Vorbedingung des Pilotstarts. Bis T-63 stand das
Routing dreifach kopiert in `embedding.py`, `generation.py`, `quiz.py` und
`self_check.py` — der Wechsel funktionierte über ENV, aber die Abstraktion, auf
die sich die NFA beruft, gab es im Code nicht. Ein Anbieter, der ein viertes
Argument braucht, wäre ein Vier-Datei-Change gewesen, und jedes neue LLM-Feature
hätte den Block ein fünftes Mal kopiert.

Was hier **nicht** hingehört, weil es sich je Call-Site fachlich unterscheidet:

- das Modell (`llm_model` gegen `embed_model`),
- Timeout und `num_retries` — beide sind pro Aufruf begründet und stehen als
  Konstante in ihrem Modul (`generation.py` retryt bewusst nicht, `embedding.py`
  zweimal), und `eval/profiles.py` überschreibt genau diese Modulkonstanten,
- `temperature`, `max_tokens`, `response_format`.

Es geht also ausschliesslich um die Frage „welcher Endpunkt, welcher Schlüssel".
"""

from typing import Any

from app.config import settings


def provider_args() -> dict[str, Any]:
    """Endpunkt und Zugangsdaten für einen LiteLLM-Aufruf.

    Per Aufruf aus `Settings` gelesen, nicht beim Import eingefroren: ein
    geänderter Endpunkt greift damit beim nächsten Aufruf, und `monkeypatch` auf
    `settings` wirkt in den Tests ohne Reload dieses Moduls.

    Die beiden Feinheiten, die diese drei Zeilen überhaupt nötig machen:

    `or None` — die Defaults der drei Settings sind `""`, und ein leerer String
    ist für LiteLLM nicht `None`. Er würde als `api_base` verwendet und bräche
    genau den OpenAI-Direct-Pfad, der im MVP ausgeliefert wird.

    `api_key` explizit statt über die Umgebung — pydantic-settings lädt `.env`
    in `Settings`, ohne nach `os.environ` zu exportieren. Ein Worker, der
    ausserhalb von docker compose startet (das exportiert via `env_file`), fände
    den Schlüssel sonst nicht, obwohl er in `.env` steht.
    """
    return {
        "api_base": settings.litellm_base_url or None,
        "api_version": settings.litellm_api_version or None,
        "api_key": settings.litellm_api_key or settings.openai_api_key,
    }
