# Ü2 · CLAUDE.md testen
**Zeit:** 10:15 – 11:00  
**Thema:** Regeln schreiben, befolgen lassen

---

## Hintergrund — Warum CLAUDE.md alles verändert

Wenn Claude Code im Projekt startet, sucht es automatisch nach einer Datei `CLAUDE.md` im Projektordner. Was darin steht, liest Claude bei JEDEM Prompt mit — ohne dass ihr es wiederholt.

Das ist **Layer 3 aus der Karpathy-Methode (Environment):** Statt bei jedem Prompt euren Stack und eure Konventionen zu wiederholen, schreibt ihr es EINMAL in `CLAUDE.md`. Danach kennt Claude euren Kontext.

In dieser Übung testet ihr das direkt: Ihr schreibt Regeln, gebt dann eine Aufgabe OHNE die Regeln zu erwähnen — und schaut ob Claude sie befolgt. Das ist der Aha-Moment.

---

## Aufgabe 1 · CLAUDE.md erstellen (15 Min)

Schreibt eine `CLAUDE.md` mit Konventionen für EUREN Stack:

```
> Erstelle eine CLAUDE.md für dieses Übungsprojekt.
  Stack: [EURE SPRACHE + VERSION].
  Konventionen (passt an euren Stack an):
  - Kommentare auf Deutsch
  - Funktionen brauchen Doku (Docstring/Javadoc/XML-Doc)
  - Tests mit [pytest / JUnit / xUnit / Jest]
  - Klare Namensgebung, keine Magic Numbers
```

**Reflexionsfrage:** Welche Abschnitte hat Claude in die CLAUDE.md geschrieben?

---

## Aufgabe 2 · Der Test — befolgt Claude die Regeln? (25 Min)

Gebt jetzt eine Aufgabe **OHNE** die Regeln zu wiederholen. Beobachtet ob Claude sie trotzdem befolgt:

```
> Erstelle eine Funktion die eine Temperatur von Celsius
  in Fahrenheit umrechnet, mit einem Test.
```

**Prüfliste — hat Claude diese Regeln aus eurer CLAUDE.md befolgt?**

- [ ] Kommentare auf Deutsch?
- [ ] Doku im Stil eurer Sprache (Docstring/Javadoc/XML-Doc)?
- [ ] Test mit eurem Test-Framework?
- [ ] Saubere Namensgebung wie gefordert?

> **Erkenntnis:** Das ist der Beweis dass Layer 3 (Environment) funktioniert: Ihr habt die Regeln nie im Prompt erwähnt — Claude hat sie trotzdem aus der `CLAUDE.md` gelesen und befolgt. Das gilt für jede Sprache.
