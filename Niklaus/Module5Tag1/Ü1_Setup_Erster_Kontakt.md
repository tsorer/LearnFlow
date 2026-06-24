# Ü1 · Setup & erster Kontakt
**Zeit:** 09:15 – 10:00  
**Thema:** Environment, Start, Permission

---

## Hintergrund — Die goldene Regel

Claude Code erbt die Umgebung des Terminals aus dem ihr es startet. Das ist der wichtigste Punkt — fast alle Anfängerfehler kommen daher.

**Reihenfolge ist immer:**
1. Werkzeuge/Environment bereitstellen (Python: conda/venv aktivieren; Java/.NET/Node: SDK ist meist schon im PATH)
2. In den Projektordner wechseln (`cd`)
3. Erst dann `claude` starten — wer nicht im Projektordner ist, bei dem liest Claude die CLAUDE.md nicht.

**Permission Model:** Claude fragt vor jeder Änderung um Erlaubnis. Am Anfang immer einzeln mit «Yes» bestätigen — so seht ihr jede Aktion und versteht wie Claude vorgeht.

---

## Aufgabe 1 · Sauberer Start (15 Min)

Erstellt einen Testordner und startet Claude Code korrekt für euren Stack:

1. Werkzeuge bereit? (Python: conda/venv aktivieren · Java/.NET/Node: SDK im PATH prüfen)
2. Testordner erstellen: `mkdir cc-uebung`
3. Hineinwechseln: `cd cc-uebung`
4. Claude starten: `claude`

**Reflexionsfrage:** Was zeigt Claude beim Start? (Modell, Kontext-Grösse, Ordner)

---

## Aufgabe 2 · Erste Datei + Permission Model (20 Min)

Gebt Claude eine einfache Aufgabe in EURER Sprache und beobachtet wie es um Erlaubnis fragt:

```
> Erstelle eine kleine Datei mit einer Funktion multiply,
  die zwei Zahlen multipliziert — in [Python/Java/C#/JS].
```

Probiert bewusst die Optionen aus:
- Beim ersten Mal: «1. Yes» — beobachtet was Claude macht
- Lasst Claude die Datei ausführen — jetzt fragt es nach Erlaubnis für einen Befehl (nicht Datei)
- Probiert «Tab» (amend): sagt «Ja, aber füge auch eine Funktion divide hinzu»

**Reflexionsfrage:** Was ist der Unterschied zwischen Permission für Datei-Änderung und für Befehl-Ausführung?
