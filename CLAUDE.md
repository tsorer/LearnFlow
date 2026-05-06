# LearnFlow – CLAUDE.md

Diese Datei wird von Claude Code bei jeder Session automatisch geladen.
Sie beschreibt Architektur, Konventionen und Workflows für das gesamte Projekt.

---

## Projektübersicht

**LearnFlow** ist ein Q&A-Proof-of-Concept auf Basis von Retrieval-Augmented Generation (RAG).
Ziel: Kuratierte Lerninhalte über eine Chat-UI abrufbar machen, mit sichtbaren Quellen und
einem ehrlichen „Weiß ich nicht"-Mechanismus.

- **Kontext:** CAS-Projekt, exemplarische Umsetzung, 4 Personen, ~360 Personenstunden
- **MVP-Scope:** Q&A mit Quellen + Feedback (👍/👎) + Unsicherheits-Markierung
- **Abgabe:** 30. September 2026

---

## Tech-Stack

| Schicht | Technologie |
|---|---|
| Frontend | Angular (TypeScript) |
| Backend / RAG | Python (FastAPI) |
| LLM | Azure OpenAI EU |
| Vector DB | tbd (z. B. Chroma, Qdrant) |
| Hosting | tbd |

---

## Repository-Struktur

```
LearnFlow/
├── CLAUDE.md               ← diese Datei (root context für Claude Code)
├── README.md
├── docs/
│   ├── architecture.md     ← ADRs und Stack-Entscheidungen
│   └── setup.md            ← Lokales Setup für neue Teammitglieder
├── backend/
│   ├── CLAUDE.md           ← Backend-spezifischer Claude-Kontext
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── services/       ← RAG-Logik, LLM-Anbindung
│   │   └── models/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── CLAUDE.md           ← Frontend-spezifischer Claude-Kontext
│   ├── src/
│   │   ├── app/
│   │   └── environments/
│   ├── angular.json
│   └── package.json
├── .github/
│   └── PULL_REQUEST_TEMPLATE.md
└── Artefakten/             ← CAS-Projektdokumentation (nicht Code)
```

---

## Häufige Befehle

### Backend (Python / FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Setup (einmalig)
pip install -r requirements.txt
uvicorn app.main:app --reload                        # Dev-Server starten
pytest                                               # Tests ausführen
```

### Frontend (Angular)
```bash
cd frontend
npm install                  # Dependencies installieren (einmalig)
ng serve                     # Dev-Server starten (http://localhost:4200)
ng build                     # Production-Build
ng test                      # Unit-Tests
ng lint                      # Linting
```

---

## Git-Workflow & Branching

```
main          ← immer deploybar, protected (kein direkter Push)
  └── develop ← Integrationsbranch, wird nach Sprint-Reviews in main gemergt
        ├── feature/learnflow-XX-kurzer-name   ← pro Story/Task
        ├── fix/learnflow-XX-kurzer-name        ← Bugfixes
        └── chore/setup-ci                      ← Infrastruktur/Tooling
```

**Regeln:**
- Direkte Pushes auf `main` und `develop` sind gesperrt
- Jeder PR braucht mindestens 1 Approval
- Branch-Namen immer mit Issue-Nummer: `feature/learnflow-12-qa-retrieval`
- Commit-Messages: `feat: Retrieval-Logik für Q&A implementiert` (Conventional Commits)

---

## Coding-Konventionen

### Allgemein
- Sprache im Code: **Englisch** (Variablen, Funktionen, Kommentare)
- Sprache in Doku/Commits: **Deutsch** ist OK, Englisch bevorzugt
- Keine Secrets oder API-Keys im Code – immer `.env` nutzen (`.env.example` pflegen)

### Python (Backend)
- Formatter: `black` + `isort`
- Linter: `ruff`
- Type-Hints überall verwenden
- Async-Funktionen für alle FastAPI-Endpunkte

### Angular (Frontend)
- Standalone Components bevorzugen (Angular 17+)
- Services für alle API-Calls (kein HTTP direkt in Components)
- `NgRx` oder einfacher Service-State – erst entscheiden, dann konsistent bleiben

---

## Architektur-Prinzipien

1. **RAG-Pipeline ist Core:** Retrieval → Augmentation → Generation – diese drei Schritte
   sind klar getrennte Services/Module, nicht vermischt.
2. **Konfidenz ist explizit:** Jede Antwort hat einen Konfidenz-Score. Unter Schwellwert
   → „Weiß ich nicht"-Antwort. Nie ohne diesen Check.
3. **Quellen immer mitliefern:** Kein Antwort-Objekt ohne `sources`-Feld.
4. **Kein Over-Engineering:** CAS-Projekt mit 360 h Budget. Einfachste Lösung, die
   die Anforderung erfüllt, ist die richtige Lösung.

---

## Umgebungsvariablen (`.env`)

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=...

# Vector DB
VECTOR_DB_URL=...

# App
LOG_LEVEL=INFO
```

Niemals echte Werte committen. Immer `.env.example` mit Dummy-Werten aktuell halten.

---

## Für Claude Code: Wichtige Hinweise

- **Scope-Disziplin:** Im Zweifel lieber weniger implementieren. Quiz, SSO, Admin-UI
  sind bewusst NICHT im MVP-Scope.
- **Tests:** Jede neue Funktion in `services/` braucht einen Unit-Test in `tests/`.
- **API-Kontrakt:** Änderungen am Backend-API immer im Frontend mitziehen (und umgekehrt).
  Shared types/schemas in `backend/app/models/` sind die Quelle der Wahrheit.
- **Keine Direktverbindung Frontend ↔ Azure OpenAI:** Alle LLM-Calls laufen über das Backend.
