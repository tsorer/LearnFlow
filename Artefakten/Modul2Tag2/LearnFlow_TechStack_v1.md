# LearnFlow — Tech Stack v1
*Architektur-Entscheide · Mai 2026*

---

## Übersicht

| Layer | Lokal (Dev) | Production |
|---|---|---|
| **LLM** | Ollama `qwen2.5:7b` | Azure OpenAI `gpt-4o-mini` |
| **Embeddings** | Ollama `nomic-embed-text` | Azure OpenAI `text-embedding-3-small` |
| **Vector DB** | pgvector (PostgreSQL) | pgvector (Azure PostgreSQL) |
| **RAG** | LangChain | LangChain |
| **Backend** | FastAPI (Python) | FastAPI (Python) |
| **Frontend** | Next.js (React, TypeScript) | Next.js |
| **Datenbank** | PostgreSQL lokal | Azure PostgreSQL |
| **Auth** | JWT + bcrypt | JWT + bcrypt |
| **Deployment** | Docker Compose | tbd |

Lokal ↔ Production: nur `.env`-Wechsel — kein Code-Änderung.

---

## Layer 1 — Datenbank

**PostgreSQL + pgvector**

Ein System für relationale Daten und Vektor-Suche — kein separater Vector-DB-Service.

### Schema

```sql
users
  id, username, password_hash, role, created_at

documents
  id, filename, file_path, uploaded_by → users
  status (processing | ready | error)
  uploaded_at, last_validated_at, area_id

chunks                          -- Herzstück der RAG-Pipeline
  id, document_id → documents
  content (text)
  embedding vector(1536)        -- pgvector
  chunk_index, page_number

feedback
  id, answer_id, rating (up | down), category, free_text
  created_at                    -- kein user_id (pseudonymisiert)

quiz_questions
  id, document_id → documents
  question, options (JSON), correct_answer
  explanation, source_passage
  status (pending | approved | rejected)
  created_at, reviewed_at

config
  key, value, updated_at, updated_by
```

### Entscheide

| Entscheid | Wahl | Begründung |
|---|---|---|
| Embedding-Dimension | 1536 | OpenAI `text-embedding-3-small` / `nomic-embed-text` kompatibel |
| Cascade bei Löschen | `DELETE chunks WHERE document_id` zuerst | Verhindert verwaiste Chunks in pgvector |

---

## Layer 2 — Document Processing

**PyMuPDF · python-docx · LangChain TextSplitter**

### Pipeline

```
Upload → Formatprüfung → Textextraktion → Chunking → Embedding → pgvector
```

### Chunking-Parameter

| Parameter | Wert | Begründung |
|---|---|---|
| `chunk_size` | 512 tokens | Bewährter Startpunkt für Fach-Dokumente |
| `chunk_overlap` | 50 tokens | Kontext über Chunk-Grenzen erhalten |

### Metadaten pro Chunk

```python
{
  "document_id": "uuid",
  "filename": "prozesse.pdf",
  "page_number": 3,
  "chunk_index": 7,
  "uploaded_at": "2026-05-20"
}
```

### Entscheide

| Format | Library | Sonderfall |
|---|---|---|
| PDF | PyMuPDF | Gescannte PDFs (kein Textlayer) → Fehlermeldung, kein OCR |
| DOCX | python-docx | Tabellen + Bilder werden ignoriert |
| Markdown | Built-in | Kein Problem |

**Upload ist async:** Request gibt sofort `202 Accepted + document_id` zurück. Status über `GET /documents/{id}/status` abrufbar (`processing | ready | error`).

---

## Layer 3 — RAG Pipeline

**LangChain · Ollama / Azure OpenAI**

### Ablauf pro Anfrage

```
Frage → Embedding → pgvector Similarity Search (k=4) → Prompt → LLM → Antwort + Quellen
```

### Prompt Template

```
Du bist ein Wissensassistent. Antworte immer auf Deutsch.
Beantworte die Frage ausschliesslich auf Basis der folgenden Quellen.
Wenn die Quellen keine Antwort enthalten, antworte mit:
"Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden."

Quellen:
{context}

Frage: {question}
Antwort:
```

### Konfidenz-Scoring (US-02) — Vorrang-Reihenfolge

1. Keine Chunks gefunden → sofort „Weiss ich nicht"
2. Konfidenz-Score unter konfiguriertem Schwellenwert → „Weiss ich nicht"
3. Anteil belegter Aussagen < 80 % → „Eingeschränkt belegt"
4. Anteil < 50 % → Antwort unterdrückt

### Entscheide

| Entscheid | Wahl |
|---|---|
| Retrieval k | 4 Chunks |
| Antwortsprache | Deutsch (hardcodiert im Prompt) |
| Quellenrückgabe | Chunk-Metadaten direkt mit Antwort |

---

## Layer 4 — Backend API

**FastAPI (Python)**

### Projektstruktur

```
backend/
├── main.py
├── .env
├── api/
│   ├── auth.py          # Login, JWT
│   ├── qa.py            # US-01, US-02: Fragen stellen
│   ├── documents.py     # US-04: Upload, Löschen
│   ├── feedback.py      # US-03: Feedback
│   ├── quiz.py          # US-07, US-08: Quiz
│   ├── stale.py         # US-06: Veraltete Inhalte
│   └── admin.py         # US-11: Config
├── core/
│   ├── rag.py           # LangChain Pipeline
│   ├── chunker.py       # Document Processing
│   └── embedder.py      # Ollama / Azure Embeddings
└── db/
    ├── models.py        # SQLAlchemy Models
    └── database.py      # Connection
```

### Endpoints

```
POST   /auth/login
POST   /qa/ask                   ← Lernende, Bereichsverantwortlicher
POST   /documents/upload         ← Bereichsverantwortlicher
DELETE /documents/{id}           ← Bereichsverantwortlicher
GET    /documents/{id}/status    ← Bereichsverantwortlicher
POST   /feedback                 ← Lernende
GET    /quiz/questions           ← Lernende
POST   /quiz/generate            ← Bereichsverantwortlicher
PUT    /quiz/questions/{id}      ← Bereichsverantwortlicher
GET    /stale/documents          ← Bereichsverantwortlicher
PUT    /admin/config             ← Admin
```

### Rollen-Middleware

```python
@router.post("/documents/upload")
async def upload(user = Depends(require_role("bereichsverantwortlicher"))):
    ...
```

Falscher Zugriff → `403 Forbidden`

---

## Layer 5 — Frontend

**Next.js · React · TypeScript**

### Projektstruktur

```
frontend/
├── app/
│   ├── login/
│   ├── qa/              # US-01, US-02, US-03
│   ├── documents/       # US-04 (Stefan)
│   ├── quiz/
│   │   ├── take/        # US-08 (Lara)
│   │   └── review/      # US-07 (Stefan)
│   ├── stale/           # US-06 (Stefan)
│   └── admin/           # US-11 (Admin)
├── components/
│   ├── QAInput.tsx
│   ├── AnswerCard.tsx
│   ├── SourceBadge.tsx
│   ├── ConfidenceBadge.tsx
│   └── UploadForm.tsx
└── lib/
    ├── api.ts
    └── auth.ts
```

### Seitenzugriff nach Rolle

| Seite | Lernende | Bereichsverantwortlicher | Admin |
|---|---|---|---|
| `/qa` | ✓ | ✓ | ✓ |
| `/documents` | — | ✓ | ✓ |
| `/quiz/take` | ✓ | — | — |
| `/quiz/review` | — | ✓ | — |
| `/stale` | — | ✓ | — |
| `/admin` | — | — | ✓ |

Falsche Route → Redirect auf `/qa` via Next.js Middleware.

### Libraries

| Zweck | Library |
|---|---|
| Styling | Tailwind CSS |
| Server State | React Query |
| Forms | React Hook Form |
| HTTP | Axios |

---

## Offene Entscheide

| # | Thema | Optionen |
|---|---|---|
| 1 | Deployment Production | Docker auf VM / Azure Container Apps / Azure App Service |
| 2 | Embedding-Dimension Prod | 1536 (`text-embedding-3-small`) bestätigen |
| 3 | PostgreSQL Version | 16+ empfohlen für pgvector |

---

*Stand: v1 — 2026-05-20*
