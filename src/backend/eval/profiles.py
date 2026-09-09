"""T-55: was ein Eval-Lauf variieren darf — und was nicht.

Der Eval läuft seit T-55 in-process (`eval/conftest.py`), und damit kann ein
Test technisch jede Konstante der Pipeline überschreiben. Genau deshalb steht
die Grenze hier und nicht im Ermessen der einzelnen Testdatei: erlaubt sind
das Modell und die **Zeitbudgets**, die ein langsamer Anbieter braucht.

Nicht erlaubt und bewusst nicht als Feld vorgesehen:

- `TEMPERATURE` — steht laut Kommentar in `generation.py` ausdrücklich im Code,
  weil ADR-009 gegen einen festen Korpus misst und alles über 0 zwei Läufe
  derselben Frage unvergleichbar macht.
- Die Konfidenz-Schwellen (`similarity_threshold`, `min_citation_coverage`,
  die Bandgrenzen) — das ist der Gegenstand der Messung, nicht ihr Rahmen. Ein
  Lauf, der sie verschiebt, misst eine andere Pipeline. Der Eval setzt sie
  stattdessen auf die Seed-Defaults (`conftest.py`), damit zwei Läufe
  vergleichbar sind.
- `MAX_RETRIES` — verdoppelt genau den langsamen Fall und verschiebt die
  Verteilung, auf die das Performance-NFA misst (T-22).

`tests/test_eval_profiles.py` hält diese Aufzählung gegen die Felder von
`Profile`, damit ein später hinzugefügtes Feld nicht unbemerkt an dieser
Begründung vorbeiwächst.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

#: Wohin die lokalen Profile ihre Generierungsaufrufe schicken. Bewusst **nicht**
#: über `settings.litellm_base_url`: die liest auch `embedding.py`, und ein
#: Ollama-Endpunkt dort würde die Embeddings mitnehmen — `chunks.embedding` ist
#: `vector(1536)` und an `text-embedding-3-small` gebunden (ADR-005, T-42). Als
#: `api_base` in `extra_completion_kwargs` erreicht die Adresse nur
#: `litellm.acompletion`, nie `aembedding`.
OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://host.docker.internal:11434")


@dataclass(frozen=True)
class Profile:
    """Eine Messkonfiguration.

    `name` landet im Ausgabepfad und in `run.json`, `gated` entscheidet über
    die Konsequenz: nur das ausgelieferte Profil lässt den Lauf rot werden.
    """

    name: str
    model: str
    #: Sekunden für den Generierungsaufruf. None = der Default aus dem Code.
    timeout_seconds: float | None = None
    #: Obergrenze der Antwortlänge. None = der Default aus dem Code.
    max_answer_tokens: int | None = None
    #: Sekunden für den Self-Check-Aufruf (Stufe 3).
    self_check_timeout_seconds: float | None = None
    #: Zusätzliche LiteLLM-Argumente, z.B. `{"think": False}` für Qwen3, das
    #: sonst pro Aufruf knapp eine Minute nachdenkt, ohne dass sich die
    #: Antwort ändert (gemessen am 2026-09-09).
    extra_completion_kwargs: dict[str, Any] = field(default_factory=dict)
    #: Ob `assert refusal_rate >= REFUSAL_RATE_GATE` greift. Ein Vergleichslauf
    #: gegen ein lokales Modell ist ein Messergebnis, kein gerissenes
    #: Release-Gate — beides in dieselbe rote Meldung zu giessen nähme dem Gate
    #: seine Aussage.
    gated: bool = False


#: Was ausgeliefert wird (ADR-004, MVP: OpenAI Direct). Überschreibt nichts —
#: dieses Profil misst die Pipeline so, wie sie in Produktion läuft, und ist
#: deshalb das einzige, dessen Ergebnis ein Gate ist.
PRODUCTION = Profile(name="openai", model="gpt-4o-mini", gated=True)

PROFILES: dict[str, Profile] = {
    PRODUCTION.name: PRODUCTION,
    # Lokale Vergleichsprofile. Die Budgets stammen aus einer Messung am
    # 2026-09-09: qwen3:8b schafft mit abgeschaltetem Denken 1,6-6 s pro
    # Anfrage, gemma4:26b braucht ~104 s und lief ohne die erhöhte
    # Antwortlänge durchgängig in `generation_truncated` — was der Eval als
    # Verweigerung zählen würde und die Messung wertlos machte.
    "qwen3-local": Profile(
        name="qwen3-local",
        model="ollama_chat/qwen3:8b",
        timeout_seconds=540.0,
        max_answer_tokens=2500,
        self_check_timeout_seconds=120.0,
        # `think: False`, weil Qwen3 sonst pro Aufruf rund 53 s nachdenkt und
        # dieselbe Antwort liefert — 57,5 s gegen 4,3 s bei identischem
        # Ergebnis (gemessen am 2026-09-09).
        extra_completion_kwargs={"think": False, "api_base": OLLAMA_API_BASE},
    ),
    "gemma4-local": Profile(
        name="gemma4-local",
        model="ollama_chat/gemma4:26b",
        timeout_seconds=540.0,
        max_answer_tokens=2500,
        self_check_timeout_seconds=120.0,
        extra_completion_kwargs={"api_base": OLLAMA_API_BASE},
    ),
}


def resolve(name: str | None) -> Profile:
    """Das Profil zu `EVAL_PROFILE`, oder das ausgelieferte."""
    if not name:
        return PRODUCTION
    try:
        return PROFILES[name]
    except KeyError:
        raise SystemExit(
            f"Unbekanntes EVAL_PROFILE {name!r}. Bekannt: {', '.join(sorted(PROFILES))}"
        ) from None
