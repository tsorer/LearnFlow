"""Trockentest der Git-Haelfte — ohne Agent, Key und Kosten.

    python test_staging.py

Gearbeitet wird in einem **Wegwerf-Repo** unter `tempfile`, nicht im echten:
ein Test, der `git add` im Arbeitsrepo aufruft, veraendert den Stand des
Entwicklers. Das darf ein Test nicht.

Der wichtigste Fall ist Nummer 5: gestagter Inhalt gegen Inhalt auf der Platte.
Das ist die zentrale Zusage des Moduls — und genau die, die ein naives
`open(pfad)` still bricht.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import staging

fehler: list[str] = []


def pruefe(name, ist, soll):
    if ist != soll:
        fehler.append(f"{name}: erwartet {soll!r}, war {ist!r}")
    print(f"{'ok    ' if ist == soll else 'FEHLER'} {name}")


def git(wurzel: Path, *befehl: str) -> None:
    """Git im Wegwerf-Repo. Identitaet und Signatur pro Aufruf gesetzt, damit
    der Test nicht von der globalen Git-Konfiguration des Rechners abhaengt."""
    subprocess.run(
        ("git", "-c", "user.email=test@test.invalid", "-c", "user.name=Test",
         "-c", "commit.gpgsign=false", *befehl),
        cwd=wurzel, capture_output=True, text=True, check=True, timeout=60,
    )


def schreibe(wurzel: Path, name: str, inhalt: str) -> None:
    (wurzel / name).write_text(inhalt, encoding="utf-8")


# ── 1. Repo-Wurzel ─────────────────────────────────────────────
wurzel_echt = staging.repo_wurzel()
pruefe("Wurzel enthaelt .git", (wurzel_echt / ".git").exists(), True)
pruefe("WURZEL ist die Wurzel", staging.WURZEL == wurzel_echt, True)


# ── 2. Fehler werden geworfen, nicht verschluckt ───────────────
try:
    staging.lauf("git", "diese-option-gibt-es-nicht")
    geworfen = False
except RuntimeError:
    geworfen = True
pruefe("kaputter Befehl wirft RuntimeError", geworfen, True)


# ── Wegwerf-Repo aufbauen ──────────────────────────────────────
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    w = Path(tmp)
    git(w, "init", "-q")
    schreibe(w, "basis.txt", "start\n")
    git(w, "add", "basis.txt")
    git(w, "commit", "-q", "-m", "initial")

    schreibe(w, "a.py", "# Der Standardwert bleibt\nX = 1\n")
    schreibe(w, "b.md", "# Die Entscheidung\n")
    schreibe(w, "c.py", "# nur auf der Platte, nicht gestaged\n")
    git(w, "add", "a.py", "b.md")

    # ── 3. Gestagte Pfade ──────────────────────────────────────
    pfade = set(staging.gestagte_pfade(wurzel=w))
    pruefe("gestagte Pfade gefunden", pfade, {"a.py", "b.md"})
    pruefe("ungestagte Datei fehlt", "c.py" not in pfade, True)

    # ── 4. Filter ──────────────────────────────────────────────
    nur_py = staging.gestagte_dateien(lambda p: p.endswith(".py"), wurzel=w)
    pruefe("Filter laesst nur .py durch", [p for p, _ in nur_py], ["a.py"])
    pruefe("Inhalt kommt mit", nur_py[0][1], "# Der Standardwert bleibt\nX = 1\n")

    keiner = staging.gestagte_dateien(lambda p: False, wurzel=w)
    pruefe("Filter kann alles ausschliessen", keiner, [])

    ohne_filter = staging.gestagte_dateien(wurzel=w)
    pruefe("ohne Filter kommt alles", len(ohne_filter), 2)

    # ── 5. Gestagt schlaegt Platte ─────────────────────────────
    # a.py nach dem `git add` weiterbearbeiten. Committet wird die gestagte
    # Fassung — also muss der Pruefer sie sehen, nicht die auf der Platte.
    schreibe(w, "a.py", "# inzwischen ganz anders\nX = 2\n")
    nachher = dict(staging.gestagte_dateien(lambda p: p.endswith(".py"), wurzel=w))
    pruefe("liest den gestagten Blob", nachher["a.py"], "# Der Standardwert bleibt\nX = 1\n")
    pruefe("nicht die Platte", "inzwischen ganz anders" not in nachher["a.py"], True)

    # ── 6. Geloeschtes faellt heraus (--diff-filter=ACM) ───────
    git(w, "rm", "-q", "basis.txt")
    pruefe("geloeschte Datei nicht dabei", "basis.txt" not in staging.gestagte_pfade(wurzel=w), True)


print()
if fehler:
    print(f"{len(fehler)} Abweichung(en):")
    for f in fehler:
        print(f"  {f}")
    sys.exit(1)
print("Git-Haelfte wie erwartet.")
