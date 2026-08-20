"""Trockentest der Kommentar-Regeln — ohne Agent, Key und Kosten.

    python test_comment_rules.py

Der wichtigste Teil sind die Fehlalarme: was NICHT anschlagen darf. Ein Pruefer,
der bei jedem englischen Satz mit einem Fachbegriff meckert, wird nach zwei
Tagen abgeschaltet.
"""

import sys

from comment_rules import einstufen, pruefe_datei, signale

fehler: list[str] = []


def pruefe(name, ist, soll):
    if ist != soll:
        fehler.append(f"{name}: erwartet {soll!r}, war {ist!r}")
    print(f"{'ok    ' if ist == soll else 'FEHLER'} {name}")


# ── Einstufung ─────────────────────────────────────────────────
def stufe(text):
    return einstufen(signale(text))


pruefe("deutscher Satz", stufe("Prueft, ob die Datei geaendert wurde"), "sicher")
pruefe("Umlaut + Stoppwort", stufe("Die Schwelle wird überschritten"), "sicher")
pruefe("nur Transliteration", stufe("Fallback fuer den Standardwert"), "sicher")
pruefe("englischer Satz", stufe("Checks whether the file was changed"), "unauffaellig")
pruefe("Code-Fragment", stufe("returns None if empty"), "unauffaellig")

# Der Zweifelsfall, fuer den es den Agent gibt: englischer Satz, deutscher
# Fachbegriff mit Umlaut. Ein Umlaut allein reicht nicht fuer "sicher" — genau
# solche Faelle soll das Modell entscheiden, nicht die Heuristik.
pruefe("englisch mit Fachbegriff", stufe("The Rückfall applies when the row is missing"), "verdaechtig")
# Gegenprobe: ohne Umlaut faellt der Fachbegriff gar nicht auf, was richtig ist.
pruefe("Fachbegriff ohne Umlaut", stufe("The Bereichsverantwortliche may upload"), "unauffaellig")

# Bekannte Luecke, bewusst festgehalten: deutscher Text ohne Umlaut, ohne
# Stoppwort und ohne transliterierte Form wird nicht erkannt. Die Signalliste
# breiter zu machen (Endungen wie -er, -ung) wuerde "user", "header", "config"
# treffen — der Preis waere hoeher als der Nutzen.
pruefe("Luecke: Deutsch ohne Marker", stufe("Rechnet Werte um"), "unauffaellig")

# "die" steckt in "died", "der" in "under" — darf nicht anschlagen.
pruefe("englische Woerter mit deutschen Silben", stufe("the process died under load"), "unauffaellig")
# "value"/"queue" enthalten "ue" — die Translit-Liste arbeitet mit ganzen Woertern.
pruefe("value und queue", stufe("the queue value is true"), "unauffaellig")


# ── Python: tokenize + ast ─────────────────────────────────────
PY = '''"""Prueft die Konfiguration und wirft bei kaputten Werten."""

import os

# Der Standardwert bleibt, wenn die Zeile fehlt
WERT = os.environ.get("X", "#  kein Kommentar, sondern String")


def f():
    """Returns the parsed value."""
    return 1  # fallback
'''

funde = pruefe_datei("app/config.py", PY)
texte = {f.text for f in funde}
pruefe("Python: Modul-Docstring gefunden", any(f.art == "docstring" for f in funde), True)
pruefe("Python: deutscher Kommentar gefunden", any("Standardwert" in t for t in texte), True)
pruefe("Python: String mit # ist kein Kommentar", all("kein Kommentar" not in t for t in texte), True)
pruefe("Python: englischer Docstring nicht gemeldet", all("Returns the parsed" not in t for t in texte), True)
pruefe("Python: Zeilennummern gesetzt", all(f.zeile > 0 for f in funde), True)


# ── TypeScript ─────────────────────────────────────────────────
TS = """// Prueft, ob der Upload durchging
const a = 1; // fallback
/* Mehrzeiliger Block,
   der die Datei prueft */
// See https://example.com/foo for details
const url = "https://x.test";
"""

tf = pruefe_datei("src/Upload.tsx", TS)
tt = [f.text for f in tf]
pruefe("TS: Zeilenkommentar gefunden", any("Prueft" in t for t in tt), True)
pruefe("TS: Blockkommentar gefunden", any("die Datei prueft" in t for t in tt), True)
pruefe("TS: URL loest keinen Fund aus", all("example.com" not in t for t in tt), True)


# ── YAML ───────────────────────────────────────────────────────
YAML = """# Die Schwelle fuer das Retrieval
threshold: 0.35
key: value  # inline, englisch
"""
yf = pruefe_datei("openapi.yaml", YAML)
pruefe("YAML: deutscher Kommentar gefunden", any("Schwelle" in f.text for f in yf), True)
pruefe("YAML: englischer inline nicht gemeldet", all("inline" not in f.text for f in yf), True)


# ── Nicht unterstuetzte Dateien ────────────────────────────────
pruefe("Markdown wird ignoriert", pruefe_datei("Docs/ADR.md", "# Die Entscheidung"), [])


print()
if fehler:
    print(f"{len(fehler)} Abweichung(en):")
    for f in fehler:
        print(f"  {f}")
    sys.exit(1)
print("Alle Regeln wie erwartet.")
