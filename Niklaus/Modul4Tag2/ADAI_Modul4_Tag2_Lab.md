# Lab · Dev Environment aufsetzen

**CAS Application Development with AI (ADAI) · 2026 — Modul 4 · Tag 2**
BFH Biel · Ilja Rasin

---

**Heute Nachmittag baut ihr euer komplettes Entwicklungs-Setup auf — bereit für die erste Zeile Code in Modul 5.**

## Was ihr heute abliefert — Deliverables

| # | Deliverable | Kriterium |
|---|-------------|-----------|
| 1 | GitHub Repo | Aufgesetzt · Team eingeladen · Branch-Strategie aktiv |
| 2 | Projekt-Struktur | Ordner für Backend, Frontend, Tests, Docs — mit Claude Code generiert |
| 3 | CLAUDE.md | Vollständig · committed · von Claude Code getestet |
| 4 | Funktionierendes Setup | Jedes Team-Mitglied kann das Repo klonen und Claude Code nutzen |

## Zeitplan

| Block | Zeit | Thema |
|-------|------|-------|
| L1 | 13:00–13:45 | Repo & Branches |
| L2 | 13:45–14:30 | Projekt-Struktur |
| — | 14:30–14:45 | Pause |
| L3 | 14:45–15:30 | CLAUDE.md |
| L4 | 15:30–16:00 | Abschluss |

---

## L1 · Repo & Branches aufsetzen — 13:00–13:45

*Euer gemeinsames Zuhause für den Code.*

**Eine Person erstellt das Repo, lädt die anderen ein. Dann richtet ihr gemeinsam die Branch-Strategie ein.**

### Schritt-für-Schritt

1. Neues Repo auf GitHub erstellen (privat) — Name = euer Projektname
2. Settings → Collaborators → Team-Mitglieder einladen
3. README.md mit Projektnamen + kurzer Beschreibung anlegen
4. Branch `develop` von `main` erstellen
5. Settings → Branches → Branch Protection für `main`: PR erforderlich
6. Eure GitHub Issues aus Tag 1 mit dem Repo verknüpfen

### Abgabe / Notizen

**Repo-URL:**

```
 
```

**Alle Team-Mitglieder haben Zugriff? (Namen):**

```
 
```

---

## L2 · Projekt-Struktur mit Claude Code — 13:45–14:30

*Lasst Claude Code die Ordnerstruktur generieren.*

**Jetzt nutzt ihr Claude Code zum ersten Mal produktiv: die komplette Projekt-Grundstruktur generieren.**

### Schritt 1 · Claude Code starten und Struktur generieren

```
# Im leeren Projekt-Ordner:
claude

> Erstelle die Grundstruktur für unser Projekt.
>
> Stack: [EUER STACK aus Architecture Draft]
> Architektur: [Modularer Monolith / Microservices]
>
> Erstelle:
> - Ordnerstruktur (backend/, frontend/, docs/, tests/)
> - requirements.txt bzw. package.json
> - .gitignore (Python + Node + IDE)
> - Leere __init__.py / index Dateien
> - Docker Compose für lokale Datenbank
```

### Schritt 2 · ADRs aus Modul 3 ablegen

**Kopiert eure ADR-001 und ADR-002 als Markdown-Dateien in den `docs/` Ordner. Das ist euer Architektur-Gedächtnis im Repo.**

### Abgabe / Notizen

**Welche Ordner hat Claude Code erstellt?**

```
 
```

> 💡 Prüft was Claude generiert hat **BEVOR** ihr committed. Claude macht Vorschläge — ihr entscheidet ob die Struktur zu eurem Projekt passt.

---

## L3 · CLAUDE.md finalisieren — 14:45–15:30

*Das Gedächtnis das Claude bei jedem Prompt mitliest.*

**Ihr habt heute Morgen einen Entwurf gemacht. Jetzt finalisiert ihr CLAUDE.md und committed sie ins Repo.**

### Checkliste — was in eure CLAUDE.md gehört

- [ ] `## Stack` — alle Sprachen, Frameworks, DB, mit Versionen
- [ ] `## Architektur` — eure ADR-Entscheidungen mit Referenz (ADR-001, ADR-002)
- [ ] `## Konventionen` — Test-Framework, Coverage-Ziel, Branch-Naming
- [ ] `## PR-Regeln` — wie viele Reviews, nutzt ihr Claude für Pre-Review
- [ ] `## Was Claude NICHT tun soll` — explizite Verbote
- [ ] `## Projekt-Struktur` — kurze Erklärung der Ordner

### Test · Versteht Claude Code euren Kontext?

```
# CLAUDE.md committen, dann Claude Code neu starten:
claude

> Was ist unser Tech-Stack?
> Welches Architektur-Pattern nutzen wir und warum?
> Schreib einen einfachen Health-Check Endpoint —
>   beachte unsere Konventionen.
```

### Abgabe / Notizen

**Hat Claude alles korrekt verstanden? Was mussten wir ergänzen?**

```
 
```

---

## L4 · Abschlusspräsentation — 15:30–16:00

*Zeigt euer Setup · 3 Min pro Team · Modul 4 abschliessen.*

**Jedes Team zeigt was es aufgesetzt hat. Das ist der Abschluss von Modul 4 — ihr seid jetzt bereit fürs Coding.**

### Was ihr in 3 Minuten zeigt

| Zeit | Inhalt |
|------|--------|
| 30 Sek | Euer Repo: Struktur kurz zeigen (`backend/`, `frontend/`, `docs/`) |
| 1 Min | Eure CLAUDE.md vorlesen — die wichtigsten Entscheidungen |
| 1 Min | Live: Claude Code fragen «Was ist unser Stack?» — zeigt dass es funktioniert |
| 30 Sek | Eure Team-Rollen + wie ihr Sprint 1 angeht |

---

## Modul 4 abgeschlossen — was ihr jetzt habt

**Bereits vorhanden:**
- ✅ Architecture Draft (Modul 3)
- ✅ Requirements Document (Modul 2)
- ✅ Sprint 1 Backlog im GitHub Board
- ✅ Klare Team-Rollen

**Heute dazugekommen:**
- ✅ Git-Workflow definiert
- ✅ GitHub Repo aufgesetzt
- ✅ CLAUDE.md geschrieben
- ✅ Projekt-Struktur steht

---

## 🚀 Ausblick Modul 5 — jetzt wird gecodet

Ab Modul 5 schreibt ihr echten Code — mit AI als Partner:

- **Modul 5A** — Claude Code CLI & Cursor: euren ersten Sprint-Task implementieren
- **Modul 5B** — OpenAI Agents SDK: eigene Agenten bauen

> ⚠️ **Wichtig für Modul 5A:** Bringt euren Laptop mit installiertem Claude Code. Wer es noch nicht hat — installiert es vorher (siehe Installations-Slide).

---

*CAS ADAI 2026 · BFH Biel · Modul 4 Tag 2 · Ilja Rasin*
