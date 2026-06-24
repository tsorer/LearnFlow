# Ü3 · Iterieren & Git
**Zeit:** 11:00 – 12:00  
**Thema:** Code ändern, committen, pushen

---

## Hintergrund — Iteration und Selbstverifikation

Claude Code ändert bestehenden Code mit einem **Update** (zeigt einen Diff: rot raus, grün rein), statt alles neu zu schreiben. Das ist sicherer — nur das Nötige ändert sich. Das gilt für jede Sprache.

Noch wichtiger: Bittet Claude nach einer Änderung die Tests auszuführen. Claude prüft dann seine eigene Arbeit — das ist **Layer 2 (Verifier)** in der Praxis. Vertraut nie blind, lasst immer verifizieren.

**Git-Ablauf:** Code → commit (lokal speichern) → push (auf GitHub hochladen). Git und GitHub sind sprachunabhängig — Claude macht alle Schritte für euch.

---

## Aufgabe 1 · Iteration mit Diff (15 Min)

Erweitert eure Funktion — beobachtet den Diff und die Selbstverifikation:

```
> Erweitere die Umrechnungs-Funktion: behandle auch
  ungültige Eingaben (null, leere Werte, falsche Typen).
  Behalte den bestehenden Test und füge Tests für die
  Fehlerfälle hinzu.

> führe danach die Tests aus
```

**Reflexionsfragen:**
- Was zeigt der Diff? Was war rot (raus), was grün (rein)?
- Hat Claude die Tests nach der Änderung selbst ausgeführt?

---

## Aufgabe 2 · Git: commit & push (25 Min)

Bringt euren Übungscode auf GitHub. Claude macht die Git-Schritte für euch:

```
> Initialisiere ein git Repository, mache einen Commit
  mit allen Dateien und einer sinnvollen deutschen
  Commit-Message. Benenne den Branch zu main um.

> Erstelle ein öffentliches GitHub Repo namens cc-uebung
  mit gh und pushe den main Branch.
```

> **Hinweis:** Falls «gh: command not found» — gh ist installiert aber das Terminal muss neu gestartet werden. Falls «git: Author identity unknown» — Claude setzt sie selbst, einfach bestätigen.

**Reflexionsfragen:**
- Eure GitHub Repo-URL:
- Welche Commit-Message hat Claude geschrieben? Ist sie gut?

---

## Ausblick: Lab heute Nachmittag

Jetzt kennt ihr die Werkzeuge. Am Nachmittag wird es ernst:

- Ihr nehmt einen echten Task aus eurem Sprint-Backlog
- Implementiert ihn mit Claude Code in eurem Projekt-Repo (in eurer Sprache)
- Schreibt Tests, lasst Claude verifizieren
- Commit + Push auf euer Team-Repo
