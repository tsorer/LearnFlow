# ADR-003: Datenpersistenz — PostgreSQL 16 + pgvector

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

LearnFlow braucht zwei Arten von Persistenz: **relationale Daten** (User-Accounts, Dokument-Metadaten, Feedback, Konfigurationsparameter, Quiz-Fragen) und **Vektor-Suche** (Embedding-Chunks für RAG-Retrieval). Zwei separate Datenbank-Services zu betreiben — einen relationalen und einen dedizierten Vector Store — würde Ops-Aufwand, separate Backups und ein zweites Service-Interface bedeuten. Mit pgvector existiert eine PostgreSQL-Extension, die Vektor-Suche direkt in der relationalen Datenbank ermöglicht. Die Pilotgrösse (ein Bereich, geschätzt < 500 Dokumente, < 10 000 Chunks) bleibt weit unter den Grenzen, ab denen pgvector an seine Skalierungsgrenzen stösst.

---

## Entscheidung

Wir verwenden **PostgreSQL 16 mit pgvector-Extension** als einzigen Persistenz-Service. Vektor-Chunks werden in einer `embeddings`-Tabelle mit HNSW-Index gespeichert. Relationale Daten (Users, Documents, Feedback, Config) liegen in normalen PostgreSQL-Tabellen. **Original-Dokumente (PDF, DOCX, Markdown) werden als `bytea`-Binärfeld in der `documents`-Tabelle gespeichert** — kein separater Datei-Storage. Schema-Migrationen werden mit **Alembic** verwaltet.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Ein Datenbankserver statt zwei: ein Backup, eine Verbindungskonfiguration, ein Ops-Prozess — entscheidend bei 360 h Budget.
- **+** SQL-Joins zwischen Vektor-Ergebnissen und relationalen Daten (z. B. Chunk → Dokument-Metadaten → Upload-Datum) sind in einer einzigen Query möglich — kein Application-Level-Join über zwei Services.
- **+** Original-Dokumente als `bytea` in PostgreSQL: ein einziger Backup deckt Metadaten, Embeddings und Originaldateien ab — keine separate Backup-Strategie für einen Datei-Storage.
- **+** HNSW-Index in pgvector liefert für < 10 000 Chunks Sub-100-ms-Latenz bei Similarity-Suche — ausreichend für die Performance-NFA (≤ 10 s @ p95 gesamt).
- **+** Alembic-Migrationen versionieren das Schema in Git — bei drei parallelen Entwicklern keine manuellen Schema-Sync-Konflikte.

### Negative Konsequenzen

- **−** pgvector ist kein dedizierter Vector Store: kein eingebautes Chunking, keine Metadata-Filter-Optimierungen wie Qdrant. Für den Pilot kein Problem; bei Post-MVP-Skalierung auf viele Bereiche und > 100 000 Chunks wäre eine Migration zu Qdrant/Weaviate zu evaluieren.
- **−** HNSW-Index muss bei grossen Bulk-Inserts neu aufgebaut werden. Mitigation: Dokument-Indexing läuft asynchron (Background Worker); kein Blocking des Retrieval-Pfads.
- **−** Grosse Binärobjekte (PDFs bis 100 MB) in `bytea` belasten PostgreSQL-Backup und -WAL-Logs überproportional — jeder Upload wird vollständig ins Write-Ahead-Log geschrieben. Mitigation: `lo` (Large Object) statt `bytea` evaluieren, oder Backup-Intervall auf nächtlich setzen.
- **−** Bei vielen grossen Dokumenten wächst die Datenbankgrösse schnell. Für den Pilot (geschätzt < 500 Dokumente) kein Problem. Post-MVP: Migration zu S3-kompatiblem Object Storage (z. B. MinIO) falls Datenbankgrösse oder Redundanz-Anforderungen steigen.

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Chroma (lokal, embedded)** | Kein SQL für relationale Daten; zweite Persistenzschicht nötig. Chroma ist für Prototypen praktisch, aber ohne Transaktionen und ohne Migrations-Tooling nicht produktionstauglich. |
| **Qdrant (dedizierter Vector Store)** | Exzellente Skalierung und Metadata-Filter — aber separater Service bedeutet eigenes Backup, eigene Verbindungsverwaltung und eigenes Monitoring. Kein Vorteil für < 10 000 Chunks. |
| **Supabase** | Würde PostgreSQL + pgvector + Auth + File Storage out-of-the-box liefern. Verworfen wegen Cloud-Lock-in, eingeschränkter DSGVO-Kontrolle (Datenhaltung je nach Region nicht garantierbar) und fehlender On-Prem-Option. |
| **SQLite + ChromaDB** | Minimaler Overhead, keine Serverinstallation. Verworfen weil SQLite keine echte Concurrent-Write-Fähigkeit hat und ChromaDB eine zweite Persistenzschicht erzwingt. Valide nur für lokales Dev-Testing. |

---

*Abhängigkeiten: ADR-001 (Modularer Monolith) · Nächste ADRs: ADR-004 (LLM), ADR-005 (Embedding)*
