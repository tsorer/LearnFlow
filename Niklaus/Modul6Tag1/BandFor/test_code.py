"""pytest-Tests fuer band_for() aus code.py.

Abgedeckt (Uebungsvorgabe):
- Happy Path      : je ein klarer Fall pro Band (hoch / mittel / niedrig).
- Grenzwerte      : genau auf den Schwellen (>=), knapp darunter, 0.0, negativ, gross.
- Ungueltige Eingaben:
    * falsche Typen  -> TypeError (die Funktion validiert nicht, der Vergleich wirft)
    * high <= medium -> ValueError (kein sinnvolles Mittelband)
- Vergessene Faelle (was ein fauler Entwickler uebersieht): NaN und bool.

Ausfuehren (aus diesem Ordner):  pytest test_code.py -v
"""

import math
import sys
from pathlib import Path

import pytest

# code.py liegt im selben Verzeichnis. Der Modulname `code` kollidiert mit dem
# gleichnamigen stdlib-Modul — darum das lokale Verzeichnis explizit vorne auf
# sys.path setzen, damit unser code.py gewinnt (unabhaengig vom pytest-Importmodus).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from code import band_for  # noqa: E402

# Feste Schwellen fuer die meisten Faelle: niedrig < 0.5 <= mittel < 0.8 <= hoch.
MEDIUM, HIGH = 0.5, 0.8


# ── Happy Path ──────────────────────────────────────────────────
@pytest.mark.parametrize(
    "score, erwartet",
    [
        (0.95, "hoch"),
        (0.65, "mittel"),
        (0.20, "niedrig"),
    ],
)
def test_happy_path(score, erwartet):
    assert band_for(score, MEDIUM, HIGH) == erwartet


# ── Grenzwerte ──────────────────────────────────────────────────
@pytest.mark.parametrize(
    "score, erwartet",
    [
        (0.8, "hoch"),       # genau high   -> gehoert ins hoehere Band (>=)
        (0.7999, "mittel"),  # knapp unter high
        (0.5, "mittel"),     # genau medium -> mittel (>=)
        (0.4999, "niedrig"), # knapp unter medium
        (0.0, "niedrig"),    # unterer Rand des typischen Bereichs
        (-1.0, "niedrig"),   # negativ ist erlaubt und faellt nach niedrig
        (1000.0, "hoch"),    # weit oberhalb von high
    ],
)
def test_grenzwerte(score, erwartet):
    assert band_for(score, MEDIUM, HIGH) == erwartet


# ── Ungueltige Schwellen: high <= medium -> ValueError ──────────
@pytest.mark.parametrize("medium, high", [(0.5, 0.5), (0.8, 0.5)])
def test_high_nicht_groesser_medium_wirft_value_error(medium, high):
    with pytest.raises(ValueError):
        band_for(0.6, medium, high)


# ── Ungueltige Eingaben: falsche Typen -> TypeError ─────────────
@pytest.mark.parametrize(
    "score, medium, high",
    [
        ("0.6", 0.5, 0.8),  # score als String
        (None, 0.5, 0.8),   # score None
        (0.6, "0.5", 0.8),  # medium als String
        (0.6, 0.5, None),   # high None
    ],
)
def test_falsche_typen_werfen_type_error(score, medium, high):
    with pytest.raises(TypeError):
        band_for(score, medium, high)


# ── Faelle, die ein fauler Entwickler vergisst ──────────────────
def test_nan_faellt_still_nach_niedrig():
    # NaN ist bei JEDEM Vergleich False -> keine >=-Bedingung greift, also
    # "niedrig" OHNE Fehler. Ein fauler Entwickler prueft NaN nie und haelt das
    # Ergebnis faelschlich fuer eine echte niedrige Konfidenz.
    assert math.isnan(float("nan"))  # Erinnerung, worum es geht
    assert band_for(float("nan"), MEDIUM, HIGH) == "niedrig"


def test_bool_wird_stillschweigend_als_zahl_behandelt():
    # bool ist Subklasse von int: True == 1, False == 0. band_for lehnt bool nicht
    # ab, sondern klassifiziert es als Zahl -> True (=1) landet in "hoch".
    assert band_for(True, MEDIUM, HIGH) == "hoch"
    assert band_for(False, MEDIUM, HIGH) == "niedrig"
