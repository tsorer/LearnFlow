# LearnFlow Backend – CLAUDE.md

Kontext für das Python/FastAPI-Backend. Ergänzt die root `CLAUDE.md`.

---

## Aufgabe dieses Moduls

Das Backend ist verantwortlich für:
- RAG-Pipeline (Retrieval → Augmentation → Generation)
- Azure OpenAI Anbindung
- Vector-DB-Verwaltung
- REST-API für das Angular-Frontend

---

## Verzeichnisstruktur

```
backend/
├── app/
│   ├── main.py               ← FastAPI-App, Router-Registrierung
│   ├── routers/
│   │   ├── qa.py             ← POST /api/qa  (Frage stellen)
│   │   ├── corpus.py         ← POST /api/corpus/upload
│   │   └── feedback.py       ← POST /api/feedback
│   ├── services/
│   │   ├── retrieval.py      ← Vector-DB-Suche
│   │   ├── generation.py     ← Azure OpenAI Call + Prompt
│   │   ├── confidence.py     ← Konfidenz-Score-Logik
│   │   └── corpus.py         ← Dokument-Ingestion + Chunking
│   └── models/
│       ├── qa.py             ← QARequest, QAResponse (Pydantic)
│       ├── feedback.py       ← FeedbackRequest
│       └── corpus.py         ← CorpusDocument
├── tests/
│   ├── test_retrieval.py
│   ├── test_generation.py
│   └── test_confidence.py
├── scripts/
│   └── ingest.py             ← CLI-Skript für Bulk-Upload
├── requirements.txt
├── requirements-dev.txt      ← pytest, black, ruff, etc.
└── .env.example
```

---

## API-Endpunkte

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/qa` | Frage stellen, Antwort mit Quellen erhalten |
| `POST` | `/api/feedback` | 👍/👎 + Kategorie speichern |
| `POST` | `/api/corpus/upload` | Dokument(e) in Vector-DB laden |
| `GET` | `/api/corpus/status` | Anzahl Dokumente, letzte Ingestion |
| `GET` | `/health` | Health-Check |

### QAResponse-Schema (wichtig: immer einhalten)
```python
class QAResponse(BaseModel):
    answer: str
    sources: list[Source]        # Niemals leer lassen
    confidence: float            # 0.0 – 1.0
    is_uncertain: bool           # True wenn confidence < threshold
```

---

## RAG-Pipeline

```
Frage (User)
    │
    ▼
[retrieval.py]  → Vector-DB-Suche → Top-K Chunks
    │
    ▼
[generation.py] → Prompt-Konstruktion + Azure OpenAI Call
    │
    ▼
[confidence.py] → Score berechnen, ggf. "Weiß ich nicht" setzen
    │
    ▼
QAResponse → Frontend
```

**Schwellwert für Unsicherheit:** `CONFIDENCE_THRESHOLD=0.7` (via .env konfigurierbar)

---

## Wichtige Hinweise für Claude Code

- Alle neuen Services als `async def` implementieren
- `.env`-Werte nie hardcoden – immer über `os.getenv()` oder `pydantic-settings`
- Bei Änderungen an `models/` immer prüfen, ob Frontend-Types angepasst werden müssen
- `pytest` muss grün bleiben vor jedem Commit
