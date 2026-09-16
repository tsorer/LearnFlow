# L1 · Datenfluss-Karte LearnFlow

> Modul 8 · Tag 1 · Deliverable 1 — Stand: 2026-09-09, Branch `feat/T-46-lose-typisierte-spec-felder`
> Regel: **nur was im Code steht, mit Datei-Beleg.** Alles ohne Beleg ist Vermutung und steht nicht drin.

## Kurzfassung

19 Datenarten. Persönlich zuordenbar sind: Konto-Stammdaten, Fragen der Lernenden,
generierte Antworten, Sessions, Upload-Urheberschaft, Config-Änderungen, IP-Adressen im
nginx-Log. **Keine einzige Tabelle hat eine Aufbewahrungsfrist** — es gibt im ganzen
Backend genau zwei `DELETE FROM` (Queue-Dedup und Re-Index von Chunks), sonst nur
Kaskaden an Löschungen, die niemand auslöst.

---

## Die Karte

| # | Datenart | Quelle | Speicher | Aufbewahrung | Wer/was sieht sie | Extern? |
|---|---|---|---|---|---|---|
| 1 | Konto: E-Mail, bcrypt-Hash, Rolle | `seed_users.py` (kein Registrierungs-Endpoint) | `users` | unbegrenzt, kein Lösch-Endpoint | Login-Pfad; E-Mail zusätzlich in `GET /documents` als `uploaded_by` → alle knowledge_owner/admin | nein |
| 2 | Passwort im Klartext | `POST /auth/login` Body | nur Prozessspeicher, nie geloggt | Request-Dauer | bcrypt-Verify | nein |
| 3 | JWT (sub=User-UUID, role, exp 1 h) | `create_access_token` | **nur Browser-Memory**, bewusst kein localStorage | Tab-Lebensdauer / 1 h | Client, `Authorization`-Header | nein |
| 4 | Hochgeladene Dokumente (Rohbytes ≤ 10 MB) | `POST /documents` multipart, knowledge_owner | `documents.content` (bytea) | unbegrenzt; überschrieben bei gleichem Dateinamen, sonst nur manuelles `DELETE` | knowledge_owner/admin | nein — die Bytes bleiben, ihr **Text** nicht (→ 5) |
| 5 | Dokument-Text als Chunks (+ heading, page) | Worker: Parsing → Chunking | `chunks.content` | bis Dokument gelöscht/neu indexiert | jede:r Authentifizierte über `GET /documents/{id}/content` (Fenster um zitierten Chunk); Admins sehen vollen Chunk-Text im Query-Debug | **JA** → Embedding-API, Antwort-Prompt, Self-Check-Prompt, Quiz-Prompt |
| 6 | Chunk-Embeddings (1536-dim) | Antwort der Embedding-API | `chunks.embedding` (pgvector) | wie Chunks | Retrieval | erzeugt extern, gespeichert lokal |
| 7 | **Fragen der Lernenden** (3–1000 Zeichen) | `POST /query` Body | **`answers.question`, dauerhaft** | **unbegrenzt** | **kein einziger Endpoint liest die Spalte je zurück** | **JA** — pro Frage 2–3 Mal raus: Embedding, Antwort-Prompt, ggf. Self-Check |
| 8 | Generierte Antworten + Scores | LLM-Antwort | `answers.answer_text`, `confidence_score`, `citation_coverage`, `retrieval_confidence`, `self_check_passed`, `suppressed` | unbegrenzt | nur Response an den Fragenden; danach nichts | **JA** — geht im Self-Check-Prompt nochmals raus |
| 9 | Query-Session (verbindet Frage ↔ Person) | `POST /query` | `query_sessions.user_id` (FK, ON DELETE SET NULL) | unbegrenzt | — | nein |
| 10 | Feedback: helpful, Kategorie, Freitext ≤ 500 Z. | `POST /answers/{id}/feedback` | `feedback` — **bewusst ohne `user_id`** | unbegrenzt | knowledge_owner/admin über `GET /feedback` (ohne `answer_id`) | nein |
| 11 | Quiz-Fragen + `source_excerpt` (Kopie des Chunk-Texts) | LLM aus Chunks | `quiz_questions` | Kaskade mit Dokument | Lernende (approved), knowledge_owner (Review) | **JA** — aus einem LLM-Call erzeugt |
| 12 | Config + Änderungs-Urheber | `PUT /admin/config` | `config.changed_by`, `changed_at` | unbegrenzt | admin | nein |
| 13 | Job-Payload | `enqueue_document` | `pgqueuer.payload` = `{"document_id": …}` | bis Job fertig | Worker | nein |
| 14 | Job-Historie inkl. Traceback | pgqueuer | `pgqueuer_log` (`traceback` JSONB) | **unbegrenzt, keine Aggregation/TTL aktiv** | DB-Zugriff | nein |
| 15 | App-Logs: `user_id`, `document_id`, Exceptions | `logging` → stdout | Docker `json-file` — **kein `logging:`-Block, also keine Rotation, keine Grössenbegrenzung** | bis Container/Host aufgeräumt wird | jede:r mit `docker logs` | nein |
| 16 | nginx-Access-Log: **Client-IP**, Pfad, Status, User-Agent | nginx | Container-stdout, default combined format | wie 15 | wie 15 | nein |
| 17 | `documents.error_message` | Worker-Fehlerpfad | `documents` | bis nächster erfolgreicher Lauf | alle knowledge_owner/admin | nein |
| 18 | Secrets: `OPENAI_API_KEY`, `JWT_SECRET`, `DB_PASSWORD` | `src/.env` (gitignored) | Container-Env | — | Prozesse in api/worker; Fragment landet bei Auth-Fehler im Worker-Log | nein |
| 19 | Rate-Limit-Zähler `account:<uuid>` / `address:<ip>` | slowapi | Prozessspeicher | bis Neustart | — | nein |

**Nicht personenbezogen, aber extern:** `LearningCorpus/` (EU AI Act, SKOS-Richtlinien,
SAMW-Leitfaden — alles öffentlich) wird über `seed_corpus.py` indexiert und geht damit
vollständig an die Embedding-API.

**Ausserhalb der Laufzeit:** der Workflow *Claude Code Review* schickt bei jedem PR den
Repository-Inhalt an die Anthropic-API (`secrets.ANTHROPIC_API_KEY`). Die Unit-Tests
selbst rufen nichts extern auf — CI setzt `OPENAI_API_KEY: sk-dummy`.

---

## Datei-Belege

| # | Beleg |
|---|---|
| 1 | `src/backend/app/models/tables.py:63` (`User`) · `src/backend/seed_users.py:14` · `src/backend/app/routers/documents.py:66` (E-Mail statt UUID in der Antwort) |
| 2 | `src/backend/app/routers/auth.py:16` · `src/backend/app/auth/jwt.py:16` |
| 3 | `src/backend/app/auth/jwt.py:36` · `src/frontend/src/App.tsx:13` · `src/frontend/src/auth.test.tsx:52` |
| 4 | `src/backend/app/routers/documents.py:38` (`MAX_UPLOAD_BYTES`), `:138` (Upload), `:220` (`_find_by_filename` → Ersetzung), `:380` (`DELETE`) · `tables.py:76` (`Document`) |
| 5 | `src/backend/worker/main.py:100` (`prepare_chunks`), `:237` (`DELETE FROM chunks`) · `tables.py:129` (`Chunk`) · `src/backend/app/routers/documents.py:325` (Fenster-Endpoint, jede Rolle) · `src/backend/app/routers/query.py:509` + `:526` (`user.role == "admin"`) |
| 6 | `src/backend/app/services/embedding.py:36` (`embed_texts`) · `worker/main.py:46` (`INSERT_CHUNK`) |
| 7 | `src/backend/app/routers/query.py:223` (`QueryRequest`), `:606` (`Answer(question=…)`) · `src/backend/app/services/retrieval.py:197` (`embed_texts([question])`) · `src/backend/app/services/generation.py` (`build_prompt`) · `src/backend/app/services/self_check.py:129` |
| 8 | `src/backend/app/routers/query.py:606–620` · `tables.py:160` (`Answer`) · `self_check.py:156` (`litellm.acompletion`) |
| 9 | `src/backend/app/routers/query.py:658` · `tables.py:151` (`QuerySession`) |
| 10 | `src/backend/app/routers/feedback.py:61` (`FeedbackRequest`), `:70` (Docstring „Pseudonymised by design"), `:126` (`FeedbackItem` ohne `answer_id`) · `tables.py:186` (`Feedback`) |
| 11 | `src/backend/app/services/quiz.py:147` (`litellm.acompletion`) · `tables.py:213` (`QuizQuestion`, `source_excerpt`) |
| 12 | `src/backend/app/routers/admin.py:95`, `:104` · `tables.py:200` (`Config.changed_by`) |
| 13 | `src/backend/app/queue.py:9` |
| 14 | `src/backend/alembic/versions/0001_pgqueuer.py:76` (`pgqueuer_log`) |
| 15 | `src/backend/worker/main.py:33` (`basicConfig`), `:120` · `src/backend/app/routers/query.py:341,371,534,561` · `src/docker-compose.yml` (kein `logging:`-Block) |
| 16 | `src/frontend/nginx.conf` (`proxy_set_header X-Real-IP $remote_addr`) |
| 17 | `src/backend/worker/main.py:120–133` · `tables.py:96` (`Document.error_message`) |
| 18 | `src/.env.example` · `src/docker-compose.yml` (`env_file: .env`) · `.gitignore:23` · `src/backend/worker/main.py:124` (Kommentar: „on an auth failure, a fragment of the API key") |
| 19 | `src/backend/app/limiter.py:11` |

---

## Was mich überrascht hat (Leitfrage L1)

1. **`answers.question` ist ein Write-Only-Archiv.** Jede je gestellte Frage liegt
   unbegrenzt in der DB, mit `query_sessions.user_id` an die Person gehängt — und
   `grep` findet keinen einzigen Endpoint, der die Spalte liest. Gesammelt „für
   später", exakt das Muster aus L3 · Grenze 1.
   Beleg: `query.py:606` schreibt, nichts liest.

2. **Das Feedback ist nur an der API-Oberfläche pseudonymisiert.** Der Code hält das
   sauber durch — `feedback` hat kein `user_id`, `FeedbackItem` liefert kein
   `answer_id`. Aber `feedback.answer_id → answers.session_id → query_sessions.user_id`
   ist ein Zwei-Schritt-Join in psql. Wer DB-Zugriff hat, hat die Zuordnung.
   Beleg: `tables.py:186` vs. `tables.py:151`.

3. **Der Ewigkeits-Kandidat ist der Dokument-Text, nicht das Dokument.** Die Rohbytes
   verlassen das System nie (ADR-003, bytea). Ihr vollständiger Textinhalt geht
   chunkweise an die Embedding-API — und beim Antworten nochmals als Prompt-Kontext.
   Ein Dokument-Upload ist damit faktisch ein Volltext-Upload zum Provider.

4. **Nichts hat eine Frist.** Kein Log-Rotate in `docker-compose.yml`, keine TTL auf
   `pgqueuer_log`, kein Cleanup auf `answers`/`query_sessions`. Der einzige Pfad, auf
   dem in diesem System je etwas gelöscht wird, ist eine manuelle Dokument-Löschung.
