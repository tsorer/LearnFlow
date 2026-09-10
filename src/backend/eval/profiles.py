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
    #: Token-Obergrenze für das Self-Check-Urteil. Gehört in dieselbe Kategorie
    #: wie `max_answer_tokens`: ein Budget, kein Schwellenwert. Nötig, weil die
    #: 300 aus `self_check.py` für `gemma4:26b` nicht reichen — es liefert dann
    #: `finish_reason='length'` bei **null** Zeichen, was fail-closed als
    #: unlesbares Urteil zählt. Mit 1000 antwortet dasselbe Modell auf denselben
    #: Prompt mit `GEDECKT` (gemessen 2026-09-09). Der Unterschied ist nicht die
    #: Länge des Urteils — sieben Zeichen —, sondern unsichtbarer Vorlauf, den
    #: das Modell gegen das Budget rechnet.
    max_verdict_tokens: int | None = None
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
    # Lokale Vergleichsprofile, alle Werte aus Messungen am 2026-09-09.
    #
    # Zu den Budgets: lokal kostet ein Token nichts, aber Zeit. Die Grenzen sind
    # so gesetzt, dass `generation_truncated` als *Messartefakt* ausgeschlossen
    # ist — ein abgeschnittener Lauf zählt im Eval als Verweigerung und sagt
    # nichts über Urteilsfähigkeit. Das Timeout zieht mit: bei den gemessenen
    # 12,8 tok/s bräuchten 8000 Tokens rund 10 Minuten, und ein zu knappes
    # Zeitbudget tauschte nur einen Abbruch gegen den anderen.
    #
    # `num_ctx` ist der wichtigste Eintrag hier und der am leichtesten zu
    # übersehende. **Ollama nimmt 4096, wenn nichts gesetzt ist**, unabhängig
    # davon, was das Modell könnte (gemma4:26b: 262144, qwen3:8b: 40960). Unsere
    # Grounding-Prompts tragen fünf Kontext-Chunks und liegen bei 7000-9000
    # Zeichen, also grob 2200-2900 Token — zusammen mit `num_predict` sprengt
    # das 4096 um ein Vielfaches, und Ollama kürzt den Prompt **von vorn**:
    # genau dort steht die Systemanweisung mit dem WEISS_NICHT-Protokoll.
    #
    # Der erste Messlauf am 2026-09-09 lief in diese Falle. `gemma4:26b` gab bei
    # den beiden längsten Prompts eine komplett leere Antwort zurück
    # (`finish_reason='length'` bei null Zeichen), was der Eval als Verweigerung
    # zählte und eine Refusal-Rate von 100 % ergab. Derselbe Prompt mit
    # `num_ctx=16384`: `finish_reason='stop'`, 311 Zeichen — und inhaltlich eine
    # *Antwort* auf eine Out-of-Corpus-Frage. Die Messung hatte also das
    # Gegenteil dessen ausgewiesen, was das Modell tat.
    "qwen3-local": Profile(
        name="qwen3-local",
        model="ollama_chat/qwen3:8b",
        timeout_seconds=1800.0,
        max_answer_tokens=8000,
        self_check_timeout_seconds=600.0,
        max_verdict_tokens=1000,
        # `think: False`, weil Qwen3 sonst pro Aufruf rund 53 s nachdenkt und
        # dieselbe Antwort liefert — 57,5 s gegen 4,3 s bei identischem
        # Ergebnis (gemessen am 2026-09-09).
        extra_completion_kwargs={"think": False, "api_base": OLLAMA_API_BASE, "num_ctx": 16384},
    ),
    "gemma4-local": Profile(
        name="gemma4-local",
        model="ollama_chat/gemma4:26b",
        timeout_seconds=1800.0,
        max_answer_tokens=8000,
        self_check_timeout_seconds=600.0,
        max_verdict_tokens=1000,
        extra_completion_kwargs={"api_base": OLLAMA_API_BASE, "num_ctx": 16384},
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
