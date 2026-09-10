"""T-55: die Grenze, die `monkeypatch` nicht mehr zieht.

Seit der Eval in-process läuft (`eval/conftest.py`), könnte ein Test technisch
jede Konstante der Pipeline überschreiben — auch `TEMPERATURE` oder die
Konfidenz-Schwellen. Das Werkzeug hält niemanden davon ab, also hält es diese
Datei fest: ein Profil darf das Modell und Zeitbudgets setzen, sonst nichts.

Unit-Test, kein Eval: läuft in `make qa` mit, braucht weder Datenbank noch
Provider, und schlägt damit *bevor* jemand eine Messung auf eine Pipeline
loslässt, die nicht mehr die ausgelieferte ist.
"""

from dataclasses import fields

from app.services import generation
from eval.profiles import PRODUCTION, PROFILES, Profile, resolve

#: Was ein Profil setzen darf. Kommt ein Feld dazu, ohne hier aufgeführt zu
#: sein, ist das keine Formalie: es hiesse, dass eine Messung an einer Stelle
#: von der Produktion abweichen kann, über die niemand entschieden hat.
ALLOWED_OVERRIDES = {
    "timeout_seconds",
    "max_answer_tokens",
    "self_check_timeout_seconds",
    # Budget, kein Schwellenwert — verschiebt nicht, *wann* eine Antwort als
    # gedeckt gilt, sondern nur, wie viel Raum das Modell für sein Urteil hat.
    # Aufgenommen, weil `gemma4:26b` mit den 300 aus `self_check.py` null
    # Zeichen liefert und der Eval das fail-closed als «unlesbar» wertete.
    "max_verdict_tokens",
    "extra_completion_kwargs",
}

#: Beschreiben das Profil, greifen aber nicht in die Pipeline ein.
DESCRIPTIVE_FIELDS = {"name", "model", "gated"}


def test_a_profile_can_only_override_time_budgets():
    """Die Aufzählung im Modul-Docstring von `eval/profiles.py` gegen die
    tatsächlichen Felder. Ein neues Feld muss hier bewusst eingetragen werden —
    sonst wächst die Überschreibbarkeit still an der Begründung vorbei.
    """
    declared = {f.name for f in fields(Profile)}

    assert declared == ALLOWED_OVERRIDES | DESCRIPTIVE_FIELDS, (
        f"Neu in Profile: {sorted(declared - (ALLOWED_OVERRIDES | DESCRIPTIVE_FIELDS))} · "
        f"verschwunden: {sorted((ALLOWED_OVERRIDES | DESCRIPTIVE_FIELDS) - declared)}"
    )


def test_no_profile_can_touch_temperature_or_the_thresholds():
    """`TEMPERATURE` steht laut Kommentar in `generation.py` ausdrücklich im
    Code, weil ADR-009 gegen einen festen Korpus misst. Kein Profilfeld darf
    darauf zeigen — und die Schwellen sind Gegenstand der Messung, nicht ihr
    Rahmen.
    """
    forbidden = {
        "temperature",
        "similarity_threshold",
        "min_retrieval_confidence",
        "min_citation_coverage",
        "confidence_threshold_high",
        "confidence_threshold_medium",
        "self_check_band_low",
        "self_check_band_high",
        "max_retries",
    }

    assert {f.name for f in fields(Profile)} & forbidden == set()
    # Der Wert selbst, damit ein späteres "nur für einen Versuch" auffällt.
    assert generation.TEMPERATURE == 0.0


def test_the_production_profile_overrides_nothing():
    """Es misst die Pipeline so, wie sie ausgeliefert wird — deshalb ist es das
    einzige, dessen Ergebnis ein Gate sein darf."""
    assert PRODUCTION.gated is True
    assert PRODUCTION.timeout_seconds is None
    assert PRODUCTION.max_answer_tokens is None
    assert PRODUCTION.self_check_timeout_seconds is None
    assert PRODUCTION.extra_completion_kwargs == {}


def test_only_the_production_profile_is_gated():
    """Ein Vergleichslauf ist eine Messreihe. Würde er dieselbe rote Meldung
    erzeugen wie ein gerissenes Release-Gate, verlöre das Gate seine Aussage."""
    gated = {name for name, p in PROFILES.items() if p.gated}

    assert gated == {PRODUCTION.name}


def test_resolve_falls_back_to_production_and_rejects_typos():
    assert resolve(None) is PRODUCTION
    assert resolve("") is PRODUCTION
    assert resolve("qwen3-local").model.startswith("ollama_chat/")

    # Kein stiller Rückfall auf die Produktion: ein Tippfehler im Profilnamen
    # würde sonst ein Gate-Ergebnis liefern, das wie eine Messung aussieht.
    try:
        resolve("qwen3")
    except SystemExit as exc:
        assert "Unbekanntes EVAL_PROFILE" in str(exc)
    else:
        raise AssertionError("ein unbekanntes Profil muss abbrechen")


def test_a_profile_that_redirects_the_endpoint_also_drops_the_api_key():
    """Sonst geht der produktive OpenAI-Key an den lokalen Endpunkt.

    `generation.py` reicht `settings.litellm_api_key or settings.openai_api_key`
    an `litellm.acompletion` weiter, und die Ollama-Transformation von LiteLLM
    macht daraus einen `Authorization: Bearer`-Header, sobald der Key nicht
    `None` ist. Ein Profil, das nur `api_base` umbiegt, schickt ihn also mit —
    nachgewiesen an `qwen3-local` und `gemma4-local` (Review zu #128).

    Als Test und nicht als Kommentar, weil der Fehler unsichtbar ist: der Lauf
    funktioniert, die Messung stimmt, und nichts in der Ausgabe deutet darauf
    hin, dass ein Geheimnis den Prozess verlassen hat.
    """
    for name, profile in PROFILES.items():
        extra = profile.extra_completion_kwargs
        if "api_base" not in extra:
            continue
        assert "api_key" in extra, (
            f"Profil {name!r} biegt api_base um, setzt aber api_key nicht — "
            "der produktive Key ginge an diesen Endpunkt"
        )
        assert extra["api_key"] is None, (
            f"Profil {name!r} schickt einen api_key an einen umgebogenen Endpunkt"
        )
