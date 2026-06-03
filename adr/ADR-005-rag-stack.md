# ADR-005 · RAG-Stack: pgvector + Multilinguales Embedding-Modell

| | |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Autor** | LearnFlow Architecture Team |
| **Bezug** | US-01, US-04, QA-06 (Testability), Risiko 1 |
| **Abhängigkeit** | ADR-001 (ConfidenceScorer), ADR-002 (RAG-Pipeline), ADR-004 (LLM-Provider) |

---

## Kontext

Der RAG-Stack ist die technische Grundlage des gesamten Kernversprechens: verlässliche, quellenbelegte Antworten. Risiko 1 im Requirements-Dokument stuft die RAG-Qualität als existenzielles Go/No-Go-Risiko ein.

Der Stack umfasst drei eng gekoppelte Entscheidungen:

1. **Vektor-Datenbank** — wo Embeddings gespeichert und Ähnlichkeitssuchen durchgeführt werden
2. **Embedding-Modell** — wie Text in Vektoren umgewandelt wird
3. **Chunking-Strategie** — wie Dokumente in Retrieval-Einheiten zerlegt werden

Alle drei beeinflussen die Retrieval-Qualität und müssen gemeinsam im Spike evaluiert werden.

### Anforderungen aus den Requirements

| Anforderung | Quelle | Implikation für RAG-Stack |
|---|---|---|
| Dokumente: PDF, DOCX, Markdown | US-04 | Parser für 3 Formate nötig |
| ≤ 50 Seiten / 10 MB → 5 min Indexierungszeit | US-04 | Asynchrones Chunking + Embedding |
| Quellenreferenz: Titel + Abschnitt + Upload-Datum | US-01 | Chunks müssen Herkunftsmetadaten tragen |
| Klick → Originaldokument mit Highlight | US-01 | Chunks müssen Offset/Seitenzahl speichern |
| Neue Version ersetzt bestehendes Dokument | US-04 | Re-Indexierung mit Versionierung |
| Sprache: Deutsch (MVP) | Requirements | Embedding-Modell muss Deutsch unterstützen |
| Out-of-Corpus „Weiss ich nicht" ≥ 90 % | US-02 | Retrieval-Score als Konfidenz-Signal |

---

## Entscheidung

### Komponente 1 · Vektor-Datenbank: pgvector (PostgreSQL-Extension)

Für das MVP wird **pgvector** als Vektor-Datenbank eingesetzt — als Extension der bereits vorhandenen PostgreSQL-Instanz.

```sql
-- Extension aktivieren
CREATE EXTENSION IF NOT EXISTS vector;

-- Chunks-Tabelle mit Embedding-Spalte
CREATE TABLE document_chunks (
  id             BIGSERIAL   PRIMARY KEY,
  document_id    UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index    INTEGER     NOT NULL,        -- Position im Dokument
  content        TEXT        NOT NULL,        -- Rohtext des Chunks
  embedding      vector(1024) NOT NULL,       -- Dimensionen je nach Modell
  page_number    INTEGER,                     -- für PDF-Highlight (US-01)
  char_offset    INTEGER,                     -- Zeichenposition im Dokument
  token_count    INTEGER     NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW-Index für schnelle Ähnlichkeitssuche
CREATE INDEX ON document_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

```sql
-- Ähnlichkeitssuche mit Score
SELECT
  dc.content,
  dc.page_number,
  dc.char_offset,
  d.title          AS document_title,
  d.uploaded_at,
  1 - (dc.embedding <=> $1::vector)  AS cosine_similarity
FROM document_chunks dc
JOIN documents d ON d.id = dc.document_id
WHERE d.area_id = $2                          -- Bereichsisolation (US-04)
ORDER BY dc.embedding <=> $1::vector
LIMIT $3;                                     -- top-k, konfigurierbar
```

**Upgrade-Pfad zu Qdrant:** Wenn das Corpus auf mehrere Bereiche (Post-MVP) oder mehrere hunderttausend Chunks wächst, wird pgvector durch Qdrant ersetzt. Der `Retriever`-Interface-Layer (siehe unten) macht diesen Wechsel transparent.

---

### Komponente 2 · Embedding-Modell: multilingual-e5-large-instruct (lokal)

Für das MVP wird **multilingual-e5-large-instruct** (Microsoft, open-source) lokal betrieben.

**Begründung für lokales Modell statt API:**
- Dokumente in Deutsch: Qualitätsvorteil eines explizit multilingualen Modells
- Keine pro-Token-Kosten für Embedding (besonders relevant beim Re-Indexieren)
- Kein zweiter API-Provider nötig — reduziert externe Abhängigkeiten (Risiko 3)
- Keine Datenschutzbedenken: Dokumenteninhalt verlässt das System nicht für Embeddings

**Modell-Spezifikation:**
| Eigenschaft | Wert |
|---|---|
| Modell | `intfloat/multilingual-e5-large-instruct` |
| Embedding-Dimension | 1 024 |
| Max. Input-Token | 512 |
| Sprachen | 100+, inkl. Deutsch |
| Grösse | ~560 MB |
| Inferenz (CPU, 512 Token) | ~150–300 ms |
| Lizenz | MIT |

```python
# EmbeddingAdapter-Interface (analog zu LLMAdapter aus ADR-002)
class EmbeddingAdapter:
    def embed_document(self, text: str) -> list[float]: ...
    def embed_query(self, query: str) -> list[float]: ...
    # Unterschiedliche Prefixes für E5-Modelle:
    # Dokument: "passage: {text}"
    # Query:    "query: {text}"

class MultilingualE5Adapter(EmbeddingAdapter):
    def __init__(self, model_path: str):
        self.model = SentenceTransformer(model_path)

    def embed_query(self, query: str) -> list[float]:
        return self.model.encode(f"query: {query}").tolist()

    def embed_document(self, text: str) -> list[float]:
        return self.model.encode(f"passage: {text}").tolist()
```

**Laufzeit-Aspekt:** Embedding bei Upload läuft asynchron (kein Request-Blocking). Embedding bei Suchanfragen (Query-Embedding) ist synchron, aber bei ~150 ms Inferenz auf CPU innerhalb des p95-Budgets von 10 s.

---

### Komponente 3 · Chunking-Strategie: Rekursiver Text-Splitter

```
Strategie: Rekursives Splitting mit Hierarchie der Trennzeichen
Reihenfolge: \n\n → \n → Satz → Wort

Chunk-Grösse:         400 Token  (Hauptwert)
Overlap:               50 Token  (Kontextkontinuität)
Mindestgrösse:         50 Token  (Filtert Artefakte)
```

**Begründung:**
- 400 Token balanciert Kontextdichte (grosse Chunks) und Präzision (kleine Chunks)
- 50-Token-Overlap verhindert, dass Aussagen an Chunk-Grenzen zerrissen werden
- Rekursive Hierarchie respektiert Absatz- und Satzgrenzen vor beliebigem Splitting

**Metadaten pro Chunk:**

```python
@dataclass
class DocumentChunk:
    content:       str
    document_id:   str
    chunk_index:   int      # Position im Dokument (für Sortierung)
    page_number:   int | None  # PDF: Seitennummer für Highlight (US-01)
    char_offset:   int      # Zeichenposition im Rohtext (für Highlight)
    token_count:   int
    embedding:     list[float]  # befüllt nach Embedding-Schritt
```

### Gesamt-Architektur des RAG-Stacks

```
Dokument-Upload (US-04)
        │
        ▼
┌───────────────────────────────────┐
│  DocumentParser                   │
│  PDF  → pdfplumber / pypdf        │
│  DOCX → python-docx               │
│  MD   → direkt                    │
│  → Rohtext + Seitenmetadaten      │
└──────────────┬────────────────────┘
               │
               ▼
┌───────────────────────────────────┐
│  ChunkingService                  │
│  Rekursiver Splitter              │
│  400 Token / 50 Overlap           │
│  → List[DocumentChunk]            │
└──────────────┬────────────────────┘
               │
               ▼
┌───────────────────────────────────┐
│  EmbeddingAdapter                 │
│  multilingual-e5-large-instruct   │
│  → embedding: list[float]         │
└──────────────┬────────────────────┘
               │
               ▼
┌───────────────────────────────────┐
│  VectorStore (pgvector)           │
│  INSERT document_chunks           │
│  HNSW-Index wird automatisch      │
│  aktualisiert                     │
└───────────────────────────────────┘


Suchanfrage (US-01)
        │
        ▼
┌───────────────────────────────────┐
│  EmbeddingAdapter.embed_query()   │
│  "query: {frage}"                 │
└──────────────┬────────────────────┘
               │
               ▼
┌───────────────────────────────────┐
│  Retriever                        │
│  SELECT ... ORDER BY cosine dist  │
│  WHERE area_id = {bereich}        │
│  LIMIT top_k (default: 5)         │
│  → List[Chunk] mit similarity     │
└──────────────┬────────────────────┘
               │
               ▼ → RAG-Pipeline (ADR-002)
```

### Retriever-Interface (abstrahiert VectorStore)

```typescript
interface Retriever {
  search(
    query:   string,
    areaId:  string,
    topK?:   number
  ): Promise<RetrievedChunk[]>
}

type RetrievedChunk = {
  content:        string
  similarity:     number   // 0.0 – 1.0, Cosinus-Ähnlichkeit
  documentTitle:  string
  uploadedAt:     Date
  pageNumber:     number | null
  charOffset:     number
  documentId:     string
}

// Produktions-Implementierung
class PgVectorRetriever implements Retriever { ... }

// Test-Implementierung
class InMemoryRetriever implements Retriever {
  constructor(private fixtures: RetrievedChunk[]) {}
  async search(): Promise<RetrievedChunk[]> { return this.fixtures }
}
```

---

## Begründung

**Warum pgvector statt einer dedizierten Vektor-Datenbank (Qdrant, Chroma)?**

pgvector nutzt die bereits im Projekt vorhandene PostgreSQL-Instanz. Keine neue Infrastrukturkomponente, kein zusätzliches Betriebswissen für das 1-FTE-Maintenance-Team. Der HNSW-Index in pgvector ist für 500 Dokumente und 20 concurrent users performant genug. Qdrant und Chroma sind bessere Optionen sobald das Corpus mehrere hunderttausend Chunks umfasst oder mehrere Bereiche hinzukommen — der Retriever-Interface-Layer erlaubt diesen Wechsel ohne Änderung an Pipeline oder Business-Logik.

**Warum lokales Embedding-Modell statt API (OpenAI text-embedding-3-small)?**

Drei Gründe: (1) Kein zweiter externer Service = keine zweite Quota-Abhängigkeit (Risiko 3). (2) Keine Embedding-Kosten beim Re-Indexieren grosser Dokumentmengen. (3) Dokumenteninhalt verlässt das System nicht — relevant wenn ADR-004 auf Azure OpenAI (Datenresidenz) setzt und konsistente Datenresidenz auch für Embeddings gelten soll. Der Nachteil (lokale Compute-Anforderung) ist bei asynchronem Upload und kurzen Query-Embedding-Zeiten (~150 ms) tolerierbar.

**Warum multilingual-e5-large-instruct und nicht ein kleineres Modell?**

Das Korrelat zu „grösser = besser" gilt bei Embedding-Modellen für Retrieval: `multilingual-e5-large` übertrifft `e5-small` bei deutschen Domänentexten deutlich (MTEB-Benchmark). Die 560 MB Modellgrösse sind bei Server-Deployment kein Problem. `multilingual-e5-base` wäre die fallback-Option wenn CPU-Inferenzzeit zu hoch.

**Warum 400-Token-Chunks, nicht 256 oder 1024?**

256 Token: zu klein, Chunks verlieren Kontext, Retrieval braucht mehr Chunks für dieselbe Abdeckung. 1024 Token: zu gross, ungenauere Semantik pro Chunk, höhere Embedding-Kosten. 400 ist ein erprobter Mittelwert für technische Fachdomänen mit mittlerer Satzlänge.

---

## Betrachtete Alternativen

### Alternative 1 · Qdrant (dedizierte Vektor-DB, self-hosted)

```
Qdrant-Container separat, REST/gRPC API
→ 3 000+ req/s, effizientes On-Disk-Indexing, filtering
```

**Zurückgestellt**: Für MVP-Corpus (500 Dokumente, 1 Bereich) Overkill. Neuer Infrastruktur-Container, Betriebsaufwand. Klarer Upgrade-Pfad wenn pgvector an Grenzen stösst.

### Alternative 2 · Chroma (lokal, einfaches Setup)

```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
```

**Abgelehnt**: Kein SQL-Join möglich (Bereichsisolation, Metadaten). Transaktionssicherheit schlechter als PostgreSQL. Persistenz auf Filesystem problematisch bei Backups.

### Alternative 3 · OpenAI text-embedding-3-small (API-basiert)

1 536 Dimensionen, sehr gute Qualität, günstig (~$0.02/M Token).

**Zurückgestellt**: Zweite externe API-Abhängigkeit (Risiko 3). Datenschutzinkonsistenz wenn LLM-Provider (ADR-004) aus Datenresidenz-Gründen Azure ist, Embeddings aber zu OpenAI US gehen. Viable Alternative wenn lokale Compute-Infrastruktur ein Problem ist.

### Alternative 4 · Cohere Embed v3 (Multilingual, API)

Explizit für RAG-Retrieval optimiert, sehr starke multilinguale Performance.

**Zurückgestellt**: Dritter externer Provider. Wenn Embedding-API gewünscht, ist OpenAI text-embedding-3-large die nächste Wahl wegen Ökosystem-Konsistenz.

---

## Konsequenzen

### Positiv
- Keine neue Infrastrukturkomponente für MVP (pgvector in bestehender PostgreSQL)
- Bereichsisolation (`WHERE area_id = ?`) nativ in SQL — keine Vektor-DB-spezifische Filter-API nötig
- Lokales Embedding: keine Embedding-API-Kosten, keine externen Daten beim Upload
- `InMemoryRetriever` macht alle Tests ohne DB und ohne Embedding-Modell ausführbar
- Metadaten (Seitenzahl, Offset) im selben DB-Record wie Embedding — kein Join zu separatem Store

### Negativ / Risiken
- pgvector HNSW-Index: bei sehr grossen Corpora (> 1M Chunks) degradiert Performance. Mitigation: Upgrade auf Qdrant via Interface-Swap
- Lokales Embedding-Modell: ~560 MB auf dem Server, ~150–300 ms CPU-Inferenz. Mitigation: Modell beim Server-Start laden (kein Cold-Start pro Request)
- Chunking-Qualität bei PDF-Tabellen und nicht-fliessenden Layouts (Formulare, Organigramme) ist eingeschränkt — diese Dokumenttypen müssen im Spike explizit getestet werden
- **Go/No-Go-Risiko (Risiko 1):** Retrieval-Qualität auf echten Dokumenten und echten Testfragen muss im Spike vor Sprint 1 validiert werden — kein theoretischer Nachweis möglich

---

## Abhängigkeiten

| Abhängigkeit | Typ | Hinweis |
|---|---|---|
| ADR-002 (RAG-Pipeline) | Konsument | `Retriever.search()` ist der erste Pipeline-Schritt |
| ADR-001 (ConfidenceScorer) | Konsument | `SemanticSimilarityScorer` nutzt denselben `EmbeddingAdapter` |
| ADR-004 (LLM-Provider) | Koordiniert | Embedding-Strategie hängt davon ab, ob Datenresidenz auch für Embeddings gilt |
| ADR-003 (ConfigService) | Konsument | `top_k`, Ähnlichkeitsschwellenwert als Config-Parameter |
| US-04 (Dokument-Upload) | Auslöser | Upload-Flow triggert Chunking + Embedding-Pipeline |
| Risiko 1 (RAG-Qualität) | Go/No-Go | Spike mit Evaluierungs-Harness (ADR-002/QA-06) vor Sprint 1 |

---

## Offen / Nächste Schritte

- [ ] **Sprint 0 Spike:** multilingual-e5-large mit echten Pilotdokumenten und Evaluierungs-Dataset testen; Metriken: Source-Hit-Rate, Out-of-Corpus-Rate, p95-Latenz
- [ ] Chunk-Grösse im Spike variieren (256 / 400 / 512 Token) und optimalen Wert messen
- [ ] PDF-Tabellenextraktion evaluieren: pdfplumber vs. pdfminer vs. pymupdf für Layoutqualität
- [ ] Embedding-Dimensionen (1 024) mit pgvector-HNSW-Performance bei erwartetem Corpus-Volumen messen
- [ ] Re-Indexierungsverhalten bei Dokumenten-Update (gleicher Dateiname, US-04) spezifizieren: Alte Chunks löschen, neue Chunks insertieren — in einer Transaktion
- [ ] `top_k` und Ähnlichkeitsschwellenwert in `config_params` eintragen (→ ADR-003)
