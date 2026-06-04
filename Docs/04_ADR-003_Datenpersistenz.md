# ADR-003: Datenpersistenz — PostgreSQL 17 + pgvector

| Feld          | Inhalt                                           |
| ------------- | ------------------------------------------------ |
| **Status**    | Proposed                                         |
| **Datum**     | 2026-05-27                                       |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

LearnFlow braucht zwei Arten von Persistenz: **relationale Daten** (User-Accounts, Dokument-Metadaten, Feedback, Konfigurationsparameter, Quiz-Fragen) und **Vektor-Suche** (Embedding-Chunks für RAG-Retrieval). Zwei separate Datenbank-Services zu betreiben — einen relationalen und einen dedizierten Vector Store — würde Ops-Aufwand, separate Backups und ein zweites Service-Interface bedeuten. Mit pgvector existiert eine PostgreSQL-Extension, die Vektor-Suche direkt in der relationalen Datenbank ermöglicht. Die Pilotgrösse (ein Bereich, geschätzt < 500 Dokumente, < 10 000 Chunks) bleibt weit unter den Grenzen, ab denen pgvector an seine Skalierungsgrenzen stösst.

---

## Entscheidung

Wir verwenden **PostgreSQL 17 mit pgvector-Extension** als einzigen Persistenz-Service. Vektor-Chunks werden in einer `embeddings`-Tabelle mit HNSW-Index gespeichert. Relationale Daten (Users, Documents, Feedback, Config) liegen in normalen PostgreSQL-Tabellen. **Original-Dokumente (PDF, DOCX, Markdown) werden als `bytea`-Binärfeld in der `documents`-Tabelle gespeichert** — kein separater Datei-Storage. Schema-Migrationen werden mit **Alembic** verwaltet.

**Versionswahl 17 (statt 16 bzw. der neuesten 18):** Die Versionswahl folgt hier *nicht* dem Wheel-Reife-Argument aus ADR-002 — pgvector ist PG-versionsunabhängig (HNSW ist ein Extension-Feature, kein PG-16/17-Feature), und Postgres-Major-Versionen sind ab Release produktionsstabil. Massgeblich sind stattdessen Docker-Image-Verfügbarkeit und Lebenszyklus: PG 17 ist zum Entscheidungszeitpunkt ~1,5 Jahre stabil, hat ein offizielles Image und pgvector-Support, und bringt gegenüber 16 Verbesserungen (Vacuum-Performance, inkrementelle Backups) mit. Gegenüber 16 spart der Start auf 17 ein späteres, vergleichsweise schmerzhaftes Major-Upgrade (`pg_upgrade`/Dump-Restore mit Downtime). PG 18 wäre vertretbar, 17 ist die konservativ-saubere Wahl; bei eurer Pilotgrösse ist der Performance-Unterschied zwischen den Versionen ohnehin vernachlässigbar.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Ein Datenbankserver statt zwei: ein Backup, eine Verbindungskonfiguration, ein Ops-Prozess — entscheidend bei 360 h Budget.
- **+** SQL-Joins zwischen Vektor-Ergebnissen und relationalen Daten (z. B. Chunk → Dokument-Metadaten → Upload-Datum) sind in einer einzigen Query möglich — kein Application-Level-Join über zwei Services.
- **+** Original-Dokumente als `bytea` in PostgreSQL: ein einziger Backup deckt Metadaten, Embeddings und Originaldateien ab — keine separate Backup-Strategie für einen Datei-Storage.
- **+** HNSW-Index in pgvector liefert für < 10 000 Chunks Sub-100-ms-Latenz bei Similarity-Suche — ausreichend für die Performance-NFA (≤ 10 s @ p95 gesamt).
- **+** Alembic-Migrationen versionieren das Schema in Git — bei vier parallelen Entwicklern keine manuellen Schema-Sync-Konflikte.

### Negative Konsequenzen

- **−** pgvector ist kein dedizierter Vector Store: kein eingebautes Chunking, keine Metadata-Filter-Optimierungen wie Qdrant. Für den Pilot kein Problem; bei Post-MVP-Skalierung auf viele Bereiche und > 100 000 Chunks wäre eine Migration zu Qdrant/Weaviate zu evaluieren.
- **−** HNSW-Index muss bei grossen Bulk-Inserts neu aufgebaut werden. Mitigation: Dokument-Indexing läuft asynchron (Background Worker); kein Blocking des Retrieval-Pfads.
- **−** pgvector indexiert HNSW nur bis **2000 Dimensionen**. Die in ADR-005 gesetzten Embedding-Dimensionen (1536 / 1024) liegen darunter; ein späterer Wechsel auf ein höherdimensionales Modell (z. B. `text-embedding-3-large`, 3072) erfordert Matryoshka-Reduktion auf ≤ 2000 oder den `halfvec`-Typ (HNSW bis 4000). Constraint bei der Embedding-Modellwahl (→ ADR-005) zu beachten.
- **−** Grosse Binärobjekte in `bytea` belasten PostgreSQL-Backup und -WAL-Logs überproportional. **Entscheid (2026-06-03):** Hartes Upload-Limit von **10 MB** serverseitig durchsetzen (US-04 spezifiziert dieses Limit bereits). WAL-Last damit beherrschbar; `lo` (Large Object)-Evaluation entfällt für MVP. Backup-Intervall: nächtlich.
- **−** Bei vielen grossen Dokumenten wächst die Datenbankgrösse schnell. Für den Pilot (geschätzt < 500 Dokumente) kein Problem. Post-MVP: Migration zu S3-kompatiblem Object Storage (z. B. MinIO) falls Datenbankgrösse oder Redundanz-Anforderungen steigen.

---

## Abgewogene Alternativen

| Alternative                                                     | Warum verworfen                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Chroma (lokal, embedded)**                                    | Kein SQL für relationale Daten; zweite Persistenzschicht nötig. Chroma ist für Prototypen praktisch, aber ohne Transaktionen und ohne Migrations-Tooling nicht produktionstauglich.                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **Qdrant (dedizierter Vector Store)**                           | Exzellente Skalierung und Metadata-Filter — aber separater Service bedeutet eigenes Backup, eigene Verbindungsverwaltung und eigenes Monitoring. Kein Vorteil für < 10 000 Chunks.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| **Supabase**                                                    | Würde PostgreSQL + pgvector + Auth + File Storage out-of-the-box liefern. Supabase ist Open Source und *grundsätzlich* self-hostbar (Docker) — der frühere Hinweis auf eine „fehlende On-Prem-Option" war unzutreffend. Verworfen wird es trotzdem: Self-hosted Supabase ist betrieblich schwergewichtig (viele Container — GoTrue, PostgREST, Realtime, Storage, Kong, Studio …), was bei 360 h Budget den Ops-Aufwand gegenüber einem einzelnen PostgreSQL-Container nicht rechtfertigt. Die verwaltete Cloud-Variante scheidet zusätzlich wegen Cloud-Lock-in und eingeschränkter DSGVO-/Regions-Kontrolle aus. |
| **SQLite + ChromaDB**                                           | Minimaler Overhead, keine Serverinstallation. Verworfen weil SQLite keine echte Concurrent-Write-Fähigkeit hat und ChromaDB eine zweite Persistenzschicht erzwingt. Valide nur für lokales Dev-Testing.                                                                                                                                                                                                                                                                                                                                                                                                            |
| **PostgreSQL 18 (neueste)**                                     | Vertretbar — pgvector unterstützt 18, und ein späteres Major-Upgrade entfiele länger. Verworfen zugunsten 17: am wenigsten abgehangen, und die neuen 18-Features (async I/O u. a.) bringen bei der Pilotgrösse < 10 000 Chunks keinen messbaren Vorteil. Re-Evaluierung bei Post-MVP-Skalierung.                                                                                                                                                                                                                                                                                                                   |
| **MinIO / S3-kompatibler Object Storage (für Originaldateien)** | Betrifft nur die Datei-Ablage, nicht die DB-Wahl: Originaldokumente in Object Storage statt als `bytea` würde WAL-Bloat und Backup-Last vermeiden — die sauberere Lösung bei vielen/grossen Dateien. Für den MVP zurückgestellt: bei < 500 Pilot-Dokumenten × max. 10 MB ist der WAL-/Grössen-Effekt beherrschbar, kein zweiter Service nötig. Erste Migrationsoption sobald Datenmenge oder Redundanz-Anforderungen steigen.                                                                                                                                                                                      |

---

*Abhängigkeiten: ADR-001 (Modularer Monolith) · Nächste ADRs: ADR-004 (LLM), ADR-005 (Embedding)*
