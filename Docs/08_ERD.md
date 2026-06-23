# Entity Relationship Diagram — LearnFlow

| Feld          | Inhalt                                           |
| ------------- | ------------------------------------------------ |
| **Stand**     | 2026-06-17                                       |
| **Verfasser** | LearnFlow-Team                                   |
| **Quellen**   | ADR-003 · ADR-006 · ADR-007 · ADR-008 · US-01–11 |

---

## Sprint-Status

| Farbe / Markierung | Bedeutung                          |
| ------------------ | ---------------------------------- |
| ✅ Vorhanden        | Migration bereits deployed         |
| 🔵 Sprint 1        | T-11 / T-13 — aktueller Sprint     |
| 🟡 Zukunft         | geplant, noch nicht implementiert  |
| ⬜ SHOULD / T-34    | SHOULD-Priorität, separates Issue  |

---

## Diagramm

```mermaid
erDiagram

    %% ── Bestehend ───────────────────────────────────────────
    users {
        uuid        id              PK
        varchar     email           UK
        varchar     hashed_password
        varchar     role
        boolean     is_active
        timestamp   created_at
    }

    pgqueuer {
        bigint      id           PK
        int         priority
        timestamp   created
        timestamp   updated
        timestamp   heartbeat
        timestamp   execute_after
        varchar     status
        varchar     entrypoint
        bytea       payload
    }

    %% ── Sprint 1 (T-11 / T-13) ──────────────────────────────
    documents {
        uuid        id           PK
        varchar     filename
        varchar     content_type
        bytea       content
        varchar     status
        varchar     area
        uuid        uploaded_by  FK
        int         chunk_count
        text        error_message
        timestamp   created_at
        timestamp   updated_at
        timestamp   validated_at
    }

    chunks {
        uuid        id           PK
        uuid        document_id  FK
        text        content
        vector      embedding
        tsvector    tsv
        int         chunk_index
        int         page
        text        heading
    }

    %% ── Zukunft ─────────────────────────────────────────────
    query_sessions {
        uuid        id           PK
        uuid        user_id      FK
        timestamp   created_at
    }

    answers {
        uuid        id                  PK
        uuid        session_id          FK
        text        question
        text        answer_text
        float       confidence_score
        float       citation_coverage
        float       retrieval_confidence
        boolean     suppressed
        timestamp   created_at
    }

    feedback {
        uuid        id          PK
        uuid        answer_id   FK
        boolean     helpful
        varchar     category
        text        comment
        timestamp   created_at
    }

    config {
        varchar     key         PK
        text        value
        text        description
        uuid        changed_by  FK
        timestamp   changed_at
    }

    %% ── SHOULD · T-34 ────────────────────────────────────────
    quiz_questions {
        uuid        id             PK
        uuid        document_id    FK
        text        question
        jsonb       options
        varchar     correct_answer
        boolean     approved
        timestamp   created_at
    }

    %% ── Beziehungen ──────────────────────────────────────────
    users           ||--o{ documents       : "uploads"
    users           ||--o{ query_sessions  : "initiates"
    users           ||--o{ config          : "modifies"
    documents       ||--o{ chunks          : "split into"
    documents       ||--o{ quiz_questions  : "generates"
    query_sessions  ||--o{ answers         : "contains"
    answers         ||--o{ feedback        : "receives"
```

---

## Feld-Notizen

### `documents`
| Feld | Typ | Anmerkung |
|---|---|---|
| `content` | `bytea` | Original-Datei ≤ 10 MB (ADR-003) |
| `status` | `varchar` | `queued` · `processing` · `ready` · `error` |
| `validated_at` | `timestamp` | Stale-Uhr für US-06 (reset bei Upload + Re-Validierung) |
| `embedding` | `vector(1536)` | `text-embedding-3-small`; OnPrem: 1024 (`bge-m3`) (ADR-005) |

### `chunks`
| Feld | Typ | Anmerkung |
|---|---|---|
| `embedding` | `vector(1536)` | HNSW-Index `vector_cosine_ops` m=16, ef=64 (ADR-003/007) |
| `tsv` | `tsvector` | GIN-Index, `to_tsvector('german', …)` — Sparse-Retrieval (ADR-007) |

### `config`
Konfigurierbare Parameter (ADR-007 · ADR-008 · US-02 · US-06 · US-11):

| Key | Startwert | Zweck |
|---|---|---|
| `similarity_threshold` | `0.35` | Retrieval-Gate (ADR-007) |
| `min_retrieval_confidence` | `0.40` | Stufe 1 (ADR-008) |
| `min_citation_coverage` | `0.50` | Stufe 2 (ADR-008) |
| `stale_days` | `90` | US-06 |
| `rrf_k` | `60` | RRF-Fusion (ADR-007) |
| `retrieval_top_k` | `20` | Kandidaten je Suche (ADR-007) |
| `context_top_n` | `5` | Chunks an LLM (ADR-007) |

`changed_by` + `changed_at` erfüllen das US-11-Audit-Log-Kriterium (kein separates Log nötig).

### `feedback`
Pseudonymisiert — kein `user_id`-Feld (US-03).

### `quiz_questions`
SHOULD-Priorität (US-07 / US-08). Eigenes Issue T-34, nicht im aktuellen Sprint.

---

## Migrations-Reihenfolge

| Migration | Tabellen | Status |
|---|---|---|
| `0001_pgqueuer` | `pgqueuer` | ✅ deployed |
| `0002_users` | `users` | ✅ deployed |
| `0003_documents_chunks` | `documents` · `chunks` · pgvector-Extension · HNSW · GIN | 🔵 T-11 / T-13 |
| `0004_rag_tables` | `query_sessions` · `answers` · `feedback` · `config` | 🟡 Zukunft |
| `0005_quiz` | `quiz_questions` | ⬜ T-34 |
