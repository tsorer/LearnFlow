"""Deutsche Kommentare im Code finden — die deterministische Haelfte.

Eigenstaendig: keine Projekt-Importe, kein SDK, kein Netz, kein API-Key. Damit
laeuft `python test_comment_rules.py` ohne alles — dieselbe Trennung wie bei
confidence.py.

Die Konvention (CLAUDE.md, Team-Absprache): Kommentare und Docstrings im Code
sind **englisch**, Deutsch bleibt `Docs/`, `Ops/`, README, PR-Texten und Issues
vorbehalten.

Warum ueberhaupt Python und nicht nur ein Modell: Umlaute, deutsche Fuellwoerter
und transliterierte Formen (`ueber`, `waere`, `fuer`) findet ein Regex sicher,
sofort und gratis. Wer dafuer ein LLM bezahlt, bezahlt fuer `grep`. Dieses Modul
liefert deshalb *Signale und Einstufungen*, keine Urteile — das Urteil an den
Zweifelsfaellen ist die Aufgabe des Agents.

**Bewusst nur Kommentare und Docstrings, keine Strings.** Das schliesst die
haeufigsten Fehlalarme von vornherein aus: Selektoren auf deutsche UI-Texte
(`getByRole({name: /löschen/i})`), erwartete Meldungstexte in Zusicherungen und
Mock-Antworten, die echte deutsche API-Meldungen nachbilden, sind Code — und
tauchen hier gar nicht erst auf.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass

# ── Signale ────────────────────────────────────────────────────
# Drei Arten, jede fuer sich schwach, zusammen aussagekraeftig.

UMLAUTE = re.compile(r"[äöüÄÖÜß]")

# Als ganze Woerter, sonst trifft "die" in "died" oder "der" in "under".
STOPPWOERTER = (
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "nicht", "und", "oder", "aber", "wenn", "dann", "wird", "werden", "ist",
    "sind", "war", "kann", "muss", "soll", "darf", "nur", "auch", "schon",
    "noch", "beim", "vom", "zum", "zur", "fuer", "ueber", "durch", "ohne",
    "gegen", "sich", "dass", "weil", "damit", "statt", "sonst", "keine",
    "kein", "wie", "hier", "dort", "diese", "dieser", "dieses", "man",
)
STOPP = re.compile(r"\b(" + "|".join(STOPPWOERTER) + r")\b", re.IGNORECASE)

# Transliteriertes Deutsch. Bewusst als Wortliste und nicht als Muster wie
# "ue": das traefe sonst "queue", "value", "true".
TRANSLIT = (
    "ueber", "waere", "wuerde", "koennen", "koennte", "muesste", "laesst",
    "naechste", "gruen", "geaendert", "zurueck", "fuer", "moeglich", "loeschen",
    "aendern", "pruefen", "prueft", "ueberschreibt", "hoeher", "groesser",
    "schluessel", "erfuellt", "haekchen", "gehoert", "waehrend", "ausloesen",
)
TRANS = re.compile(r"\b(" + "|".join(TRANSLIT) + r")\b", re.IGNORECASE)


def signale(text: str) -> tuple[str, ...]:
    """Deterministische Deutsch-Marker eines einzelnen Kommentars."""
    gefunden: list[str] = []
    if (u := UMLAUTE.findall(text)):
        gefunden.append(f"umlaute:{''.join(sorted(set(u)))}")
    if (s := STOPP.findall(text)):
        # Nur verschiedene Woerter zaehlen; dreimal "die" ist ein Signal, nicht drei.
        eindeutig = sorted({w.lower() for w in s})
        gefunden.append("stoppwoerter:" + ",".join(eindeutig))
    if (t := TRANS.findall(text)):
        gefunden.append("translit:" + ",".join(sorted({w.lower() for w in t})))
    return tuple(gefunden)


def einstufen(sig: tuple[str, ...]) -> str:
    """sicher · verdaechtig · unauffaellig.

    `sicher` bedeutet: kein englischer Satz sieht so aus. Mehrere verschiedene
    Stoppwoerter oder eine transliterierte Form sind fuer sich schon eindeutig.
    Ein einzelner Umlaut dagegen kann ein Fachbegriff in einem englischen Satz
    sein ("the Bereichsverantwortliche may upload") — das entscheidet der Agent.
    """
    stopp = next((s for s in sig if s.startswith("stoppwoerter:")), "")
    anzahl_stopp = len(stopp.split(":", 1)[1].split(",")) if stopp else 0
    hat_translit = any(s.startswith("translit:") for s in sig)
    hat_umlaut = any(s.startswith("umlaute:") for s in sig)

    if hat_translit or anzahl_stopp >= 2 or (anzahl_stopp >= 1 and hat_umlaut):
        return "sicher"
    if sig:
        return "verdaechtig"
    return "unauffaellig"


# ── Kommentare herausloesen ────────────────────────────────────

@dataclass(frozen=True)
class Fund:
    datei: str
    zeile: int
    art: str  # "kommentar" | "docstring"
    text: str
    signale: tuple[str, ...]
    einstufung: str


def _python(quelle: str) -> list[tuple[int, str, str]]:
    """Kommentare via tokenize, Docstrings via ast — beides exakt.

    Kein Selbstbau: `tokenize` weiss, dass ein `#` in einem String kein
    Kommentar ist, und `ast` weiss, was ein Docstring ist und was nur ein
    String am Anfang einer Funktion.
    """
    treffer: list[tuple[int, str, str]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(quelle).readline):
            if tok.type == tokenize.COMMENT:
                treffer.append((tok.start[0], "kommentar", tok.string.lstrip("# ").rstrip()))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass  # unvollstaendige Datei: Kommentare bis dahin behalten wir

    try:
        baum = ast.parse(quelle)
    except SyntaxError:
        return treffer
    for knoten in ast.walk(baum):
        if isinstance(knoten, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(knoten, clean=False)
            if doc:
                # Zeile des Docstring-Knotens, nicht des def
                erste = knoten.body[0]
                treffer.append((getattr(erste, "lineno", 1), "docstring", doc.strip()))
    return treffer


# Zeilenscanner fuer C-artige Sprachen. Bewusst einfach gehalten; die eine
# Falle, die wirklich haeufig ist, wird behandelt: `//` in einer URL.
URL = re.compile(r"https?://")


def _c_artig(quelle: str) -> list[tuple[int, str, str]]:
    treffer: list[tuple[int, str, str]] = []
    im_block = False
    for nr, zeile in enumerate(quelle.splitlines(), 1):
        rest = zeile
        if im_block:
            ende = rest.find("*/")
            text = rest if ende == -1 else rest[:ende]
            treffer.append((nr, "kommentar", text.strip(" *")))
            if ende == -1:
                continue
            im_block = False
            rest = rest[ende + 2 :]
        if (start := rest.find("/*")) != -1:
            ende = rest.find("*/", start + 2)
            if ende == -1:
                im_block = True
                treffer.append((nr, "kommentar", rest[start + 2 :].strip(" *")))
                continue
            treffer.append((nr, "kommentar", rest[start + 2 : ende].strip(" *")))
            rest = rest[ende + 2 :]
        pos = rest.find("//")
        while pos != -1 and URL.search(rest[max(0, pos - 6) : pos + 2]):
            pos = rest.find("//", pos + 2)  # Teil einer URL, weitersuchen
        if pos != -1:
            treffer.append((nr, "kommentar", rest[pos + 2 :].strip()))
    return treffer


def _raute(quelle: str) -> list[tuple[int, str, str]]:
    """YAML, Makefile: alles ab `#`, sofern die Zeile nicht damit endet."""
    return [
        (nr, "kommentar", zeile[zeile.find("#") + 1 :].strip())
        for nr, zeile in enumerate(quelle.splitlines(), 1)
        if "#" in zeile and zeile[zeile.find("#") + 1 :].strip()
    ]


ZERLEGER = {
    ".py": _python,
    ".ts": _c_artig,
    ".tsx": _c_artig,
    ".js": _c_artig,
    ".mjs": _c_artig,
    ".yaml": _raute,
    ".yml": _raute,
}


def unterstuetzt(pfad: str) -> bool:
    return any(pfad.endswith(endung) for endung in ZERLEGER) or pfad.endswith("Makefile")


def pruefe_datei(pfad: str, inhalt: str) -> list[Fund]:
    zerleger = next(
        (f for endung, f in ZERLEGER.items() if pfad.endswith(endung)),
        _raute if pfad.endswith("Makefile") else None,
    )
    if zerleger is None:
        return []
    funde: list[Fund] = []
    for zeile, art, text in zerleger(inhalt):
        if not text:
            continue
        sig = signale(text)
        if not sig:
            continue  # unauffaellige Kommentare interessieren niemanden
        funde.append(Fund(pfad, zeile, art, text, sig, einstufen(sig)))
    return sorted(funde, key=lambda f: (f.datei, f.zeile))
