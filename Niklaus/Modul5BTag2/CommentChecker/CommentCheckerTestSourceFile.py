"""Fixture for the comment checker. Stage this file, then run the checker.

Not production code and not imported by anything. Every German comment below is
deliberately placed to hit one branch of the rules, so a run has something to
find — and the traps have something to stay quiet about.

    git add CommentCheckerTestSourceFile.py
    python comment_checker.py --alle    # deterministic half only, no model
    python comment_checker.py           # model judges the doubtful ones
    git restore --staged CommentCheckerTestSourceFile.py

All scaffolding here — this docstring, the section headers, the notes — is
English on purpose. Scaffolding that trips the checker would drown the cases it
is supposed to frame. Only the material under test is German.

Expected: 4x sicher, 1x verdaechtig, everything else silent.
"""

import os


# ── Band 1: sicher ─────────────────────────────────────────────
# Two or more distinct stopwords, or a transliterated form, or one stopword
# plus an umlaut. No English sentence looks like this.

# Der Standardwert bleibt, wenn die Zeile fehlt
WERT = os.environ.get("LEARNFLOW_WERT", "#  kein Kommentar, sondern ein String")

# Prueft die Konfiguration und wirft bei kaputten Werten
LIMIT = 10

# Die Schwelle wird überschritten
SCHWELLE = 0.35


# ── Band 2: verdaechtig — this is what the model is for ────────
# A single umlaut inside an otherwise English sentence. Could be a German
# comment, could be an English one carrying a German domain term. The rules
# refuse to guess; the model decides.

# The Rückfall applies when the row is missing
def fallback(row):
    """Returns the parsed value, or None when the row is empty."""
    return row or None


# Docstrings count too, not just comments — via ast, not a regex.
def mittelwert(treffer):
    """Berechnet den Mittelwert über alle Treffer und rundet kaufmännisch."""
    return sum(treffer) / len(treffer) if treffer else 0.0


# ── Traps: must stay silent ────────────────────────────────────
# These are the false positives that would get the checker switched off.

# Checks whether the file was changed since the last run
GEAENDERT = False

# Whole-word matching only, so nothing fires inside "died" or "under".
# the process died under load
RETRIES = 3

# "ue" hides in "queue", "value", "true" — the translit list holds whole words
# the queue value is true
TIMEOUT = 30

# A German domain term without an umlaut carries no signal, which is correct:
# the sentence is English.
# The Bereichsverantwortliche may upload documents
UPLOAD_ERLAUBT = True


# ── Known gap: German that carries no marker at all ────────────
# No umlaut, no stopword, no transliterated form. Not detected, on purpose:
# widening the signal list would start hitting "user", "header", "config".

# Rechnet Werte um
def umrechnen(wert):
    return wert * 2


# ── Strings are never checked, only comments and docstrings ────
# Both values below are German. Both are code, so neither shows up. This is
# what keeps UI selectors and expected message texts out of the report.

LABEL_LOESCHEN = "Datei löschen"
FEHLERTEXT = "Die Datei konnte nicht gespeichert werden"
