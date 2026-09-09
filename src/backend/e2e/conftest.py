"""T-55 (#123): die DB-gestützten Suiten laufen seriell — zugesichert, nicht zufällig.

`e2e` und `eval` teilen sich eine Datenbank und im Fall von `e2e` einen ganzen
Stack. Mehrere Module schreiben dieselben `config`-Zeilen (die Konfidenz-Schwellen)
und laden sich am selben Rate-Limit ein; parallel ausgeführt würden sie einander
Werte unter den Füssen wegziehen, und zwar nichtdeterministisch.

Heute passiert das nicht, aber nur weil `pytest-xdist` gar nicht installiert ist.
Das ist kein Zustand, auf den man sich verlässt: ein `-n auto` in `addopts` — der
naheliegende Griff, wenn die Suite einmal zu langsam wird — liesse sie sofort
nebeneinander auf dieselbe Datenbank los, und das Ergebnis wäre ein sprunghaft
rot werdender Lauf, dessen Ursache niemand vermutet.

Deshalb dieser Riegel: er sagt beim Start ab, statt hinterher unerklärlich zu
scheitern, und nennt den Grund. Wer wirklich parallelisieren will, muss vorher
die geteilte Datenbank auflösen — nicht diese Datei löschen.
"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    workers = config.getoption("numprocesses", default=None)
    if workers in (None, 0):
        return
    raise pytest.UsageError(
        "Die e2e-Suite teilt sich eine Datenbank und darf nicht parallel laufen "
        f"(-n {workers}). Mehrere Module schreiben dieselben `config`-Zeilen; "
        "nebeneinander ziehen sie einander die Schwellen weg. Siehe T-55 (#123)."
    )
