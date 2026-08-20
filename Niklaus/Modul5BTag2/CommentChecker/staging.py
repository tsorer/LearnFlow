"""Was gerade committet werden soll — die Git-Haelfte.

Eigenstaendig: kein SDK, kein Modell, kein API-Key. Damit laeuft
`python test_staging.py` ohne alles — dieselbe Trennung wie bei
`comment_rules.py`.

Dieses Modul weiss nichts von Kommentaren und nichts von Sprache. Es liefert
Pfad und Inhalt der gestagten Dateien; was daraus gelesen wird, entscheidet der
Aufrufer. Deshalb ist es fuer jeden weiteren Pre-Commit-Pruefer brauchbar, nicht
nur fuer den Kommentar-Check.

**Gelesen wird der gestagte Blob, nicht die Datei auf der Platte.** Wer eine
Aenderung nur teilweise staged, committet auch nur diesen Teil — und genau der
gehoert geprueft. `git show :<pfad>` liefert ihn, `open(pfad)` nicht.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path


def repo_wurzel(start: Path | None = None) -> Path:
    """Repo-Wurzel ueber Git bestimmen, statt `.parent` zu zaehlen.

    Ein fester Pfad wie `parent.parent.parent` bricht **still**, sobald der
    Ordner eine Ebene wandert: `git` laeuft dann im falschen Verzeichnis und
    meldet einen leeren Staging-Bereich statt eines Fehlers — der Pruefer waere
    gruen, ohne etwas geprueft zu haben. Genau das ist beim Umzug von
    Modul5BTag1 hierher passiert.
    """
    fertig = subprocess.run(
        ("git", "rev-parse", "--show-toplevel"),
        cwd=start or Path(__file__).resolve().parent,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    if fertig.returncode != 0:
        raise RuntimeError(f"kein Git-Repo gefunden: {fertig.stderr.strip()}")
    return Path(fertig.stdout.strip())


WURZEL = repo_wurzel()


def lauf(*befehl: str, wurzel: Path | None = None) -> str:
    """Einen Git-Befehl ausfuehren und die Ausgabe liefern.

    `befehl` ist ein Tupel und geht ohne Shell an `subprocess` — es gibt also
    keine Stelle, an der sich etwas einschleusen liesse. Fehler werden geworfen
    und nicht als leere Ausgabe getarnt: ein Pruefer, der bei kaputtem Git
    „nichts gefunden" meldet, ist schlimmer als einer, der abbricht.
    """
    fertig = subprocess.run(
        befehl, cwd=wurzel or WURZEL,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    if fertig.returncode != 0:
        raise RuntimeError(f"{' '.join(befehl)}: {fertig.stderr.strip()}")
    return fertig.stdout


def gestagte_pfade(wurzel: Path | None = None) -> list[str]:
    """Pfade der Dateien, die beim naechsten Commit landen.

    `--diff-filter=ACM` = Added, Copied, Modified. Geloeschtes (`D`) hat keinen
    Inhalt mehr zu pruefen. Umbenanntes (`R`) faellt damit allerdings auch
    heraus — bekannte Luecke, siehe README.
    """
    roh = lauf("git", "diff", "--cached", "--name-only", "--diff-filter=ACM",
               wurzel=wurzel).strip()
    return [p for p in roh.splitlines() if p]


def gestagte_dateien(
    nimm: Callable[[str], bool] | None = None,
    wurzel: Path | None = None,
) -> list[tuple[str, str]]:
    """Pfad und gestagter Inhalt jeder Datei, die committet werden soll.

    `nimm` entscheidet, welche Pfade ueberhaupt interessieren — z. B.
    `comment_rules.unterstuetzt`. Ohne Filter kommt alles. Der Filter greift
    **vor** dem Lesen des Blobs, damit fuer uninteressante Dateien gar kein
    `git show` laeuft.

    Nicht lesbare Eintraege (Binaerdateien, Submodule) werden uebersprungen und
    nicht geworfen: ein einzelnes Bild im Commit darf den Pruefer nicht kippen.
    """
    dateien: list[tuple[str, str]] = []
    for pfad in gestagte_pfade(wurzel):
        if nimm is not None and not nimm(pfad):
            continue
        try:
            dateien.append((pfad, lauf("git", "show", f":{pfad}", wurzel=wurzel)))
        except RuntimeError:
            continue
    return dateien
