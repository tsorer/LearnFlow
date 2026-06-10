# L1 · Teil 2 · Kommunikation zwischen Containern klären

*LearnFlow · Modul 3 Tag 1 · Reto Stucki · 2026-05-31*

---

## Ausgangslage

C2 Container Diagram: [Docs/05_C4-C2_Container.md](../../Docs/05_C4-C2_Container.md)  
Top-3 Quality Attributes: **Reliability · Security · Maintainability**

---

## Analyse — Verbindungen im C2 Diagram

| Verbindung                                                | Sync / Async                                                     | Bei Ausfall                                                                                                                  | Bottleneck bei Last                                                                                                                |
| --------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Web App → API Server** (REST + SSE · HTTPS)             | Beides: REST synchron, SSE ist lang laufender HTTP-Stream        | Nutzer sieht leeren Screen — kein Login, kein Q&A, kein Upload möglich                                                       | 30 parallele SSE-Streams + LLM-Calls; Engpass liegt aber bei OpenAI Rate Limits, nicht bei FastAPI                                 |
| **API Server → Datenbank** (SQL · TCP 5432)               | Synchron (non-blocking mit asyncpg)                              | Vollständiger Systemausfall — Auth, Q&A, Config, Feedback: alles bricht                                                      | Similarity Search (pgvector HNSW): 30 parallele Vektor-Queries; fehlendes Connection Pooling kann zu Verbindungserschöpfung führen |
| **API Server → Background Worker** (pg_notify · TCP 5432) | Asynchron — Job landet in Queue, sofortige Bestätigung an Stefan | Jobs akkumulieren in Queue, gehen aber nicht verloren (PostgreSQL-transaktional); 5-Minuten-SLA verletzt, keine Datenverlust | Worker ist Single-Threaded: parallele Uploads stauen die Queue; Batch-Inserts für Chunks sind Pflicht                              |
| **Background Worker → Datenbank** (SQL · TCP 5432)        | Synchron — Chunks + Embeddings sequentiell geschrieben           | Job bleibt in Queue, wird bei DB-Neustart wiederholt — nur wenn Implementierung idempotent (upsert statt insert)             | Viele Chunks pro Dokument (50 Seiten ≈ 200 Chunks) = 200 INSERTs; Batch-Writes zwingend                                            |
| **API Server → OpenAI API** (HTTPS via LiteLLM)           | Synchron mit Timeout; LLM-Response als SSE-Stream zurück         | Q&A + Embedding-Indexierung down; Circuit Breaker Pflicht — nie Fallback-Text generieren, immer Fehlermeldung                | **Rate Limits nicht im Einflussbereich des Teams** — Quota-Erschöpfung bricht Q&A für alle Nutzer gleichzeitig                     |

---

## Kritischster Datenfluss — Lara stellt eine Frage

```
Lara tippt Frage
       │
       ▼
[Web App] Validierung (3–1000 Zeichen)
       │ POST /api/query (HTTPS)
       ▼
[API Server]
  1. JWT prüfen           → [DB] users              (~5 ms)
  2. Konfig lesen         → [DB] config              (~2 ms)
  3. Query embedden       → [OpenAI] embedding       (~300 ms)
  4. Similarity Search    → [DB] pgvector HNSW       (~50 ms)
  5. Quellenprüfung       → keine Quelle → "Keine Antwort"
  6. Konfidenz prüfen     → Score < Schwelle → "Weiss ich nicht"
  7. Self-Check           → < 50% → Unterdrückt
  8. LLM-Prompt           → [OpenAI] gpt-4o-mini     (SSE-Stream, ~2–8 s)
       │ text/event-stream
       ▼
[Web App] Token-by-Token anzeigen + Quellenreferenzen einblenden
```

**Gesamtlatenz kritischer Pfad:** ~2.5–9 s — p95-Ziel 10 s erreichbar, aber ohne Puffer.

---

## Kritischste Verbindung in unserem System — und warum

**API Server → OpenAI API**

Diese Verbindung ist der einzige externe Abhängigkeitspunkt ausserhalb des eigenen Stacks. Sie dominiert die Antwortlatenz (2–8 s von 10 s Budget), ist durch Rate Limits beschränkt die ausserhalb des Team-Einflusses liegen, und ist die einzige Verbindung deren Ausfall Q&A vollständig stoppt — ohne sinnvollen Fallback. Zusätzlich verlassen Unternehmensqueries die EU, was ein DSGVO-Risiko darstellt (Ollama als Fallback adressiert das, erhöht aber die Komplexität).

---

## Was passiert wenn der API Server ausfällt?

**Totaler Nutzerausfall.** Der API Server ist der zentrale Orchestrator des Systems. Bei Ausfall:

- Login nicht möglich (JWT-Ausstellung bricht)
- Q&A down — keine Fragen stellbar
- Dokument-Upload nicht entgegennehmbar
- Admin-Konfiguration nicht erreichbar

Der Background Worker läuft weiter, kann aber keine neuen Jobs empfangen. Da Single Instance ohne Load Balancer bringt Docker-Restart-Policy (`always`) den Server in ~30 Sekunden zurück — laufende SSE-Streams brechen jedoch ab und müssen manuell neu gestartet werden.

---

## Wo ist unser Single Point of Failure?

**Die Datenbank (PostgreSQL + pgvector).**

| Ausfall                 | Konsequenz                                                                    |
| ----------------------- | ----------------------------------------------------------------------------- |
| API Server fällt aus    | System down, aber in ~30 s recoverable                                        |
| OpenAI API fällt aus    | Q&A + Indexierung down, Dokumentverwaltung funktioniert noch                  |
| **Datenbank fällt aus** | **Alles** down: Auth, Q&A, Upload, Config, Jobs — kein Recovery ohne Neustart |

Die Datenbank ist zudem die einzige Kopie aller Original-Dokumente (bytea), Embeddings und der gesamten Konfiguration. Ein Datenbankausfall ist nicht nur ein Verfügbarkeits-, sondern ein **Datenverlust-Risiko**.

> **Konsequenz:** Täglicher `pg_dump` (Cron in Docker Compose) ist kein Nice-to-have — er ist Pflicht vor Pilot-Start.

---

*Quellen: [Docs/05_C4-C2_Container.md](../../Docs/05_C4-C2_Container.md) · [Docs/02_Requirements.md](../../Docs/02_Requirements.md)*
