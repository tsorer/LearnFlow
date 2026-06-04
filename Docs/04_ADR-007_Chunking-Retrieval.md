# ADR-007: Chunking- & Retrieval-Strategie — Struktur-bewusstes Chunking + Hybrid-Retrieval mit Schwellenwert-Gate

| Feld          | Inhalt                                           |
| ------------- | ------------------------------------------------ |
| **Status**    | Proposed                                         |
| **Datum**     | 2026-05-31                                       |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

Die zentrale Reliability-NFA von LearnFlow (Halluzinationsrate = 0 %, bei Out-of-Corpus-Fragen ≥ 90 % „Weiss ich nicht") hängt **nicht primär** am LLM-Provider (ADR-004) oder am Embedding-Modell (ADR-005), sondern an der **RAG-Pipeline-Qualität**: Wie Dokumente in Chunks zerlegt werden und wie relevante Chunks zur Anfrage gefunden werden, bestimmt direkt die Retrieval-Präzision — und damit, ob das LLM eine quellenbelegte Antwort bilden kann oder halluziniert.

Diese Entscheidung war bisher in keinem ADR dokumentiert, obwohl sie im Tech-Spike (Woche 1) getroffen werden muss und **teuer zu revidieren** ist: Jede Änderung an Chunking-Parametern oder Embedding erfordert eine vollständige Re-Indexierung aller Dokumente (vgl. ADR-003, ADR-005).

Randbedingungen:

- **Korpus:** deutschsprachige Fachtexte, Pilotgrösse < 500 Dokumente / < 10 000 Chunks.
- **Persistenz:** PostgreSQL 17 + pgvector (HNSW), Postgres-Volltextsuche (`tsvector`) verfügbar — beides ohne zusätzlichen Service (ADR-003).
- **Embedding:** `text-embedding-3-small` (1536 Dim) produktiv, `bge-m3` (1024) lokal (ADR-005).
- **Besonderheit Deutsch:** Komposita, Fachbegriffe und Akronyme profitieren stark von exaktem Term-Matching — reine semantische (Dense-)Suche verfehlt exakte Begriffe häufiger.

**Abgrenzung:** Dieses ADR entscheidet **Chunking + Retrieval + Grounding-Prompt-Kontrakt**. Die *Berechnung* des Konfidenz-Scores und die mehrstufige Antwort-Unterdrückung (Self-Check etc.) sind ein eigener Belang → offen für **ADR-008 (Konfidenz- & Unterdrückungspipeline)**. ADR-007 liefert dafür die retrieval-seitige Vorstufe (Schwellenwert-Gate).

---

## Entscheidung

### 1. Chunking — struktur-bewusstes, rekursives Splitting

Dokumente werden **struktur-bewusst** zerlegt: Die Pipeline respektiert zuerst natürliche Grenzen (Überschriften → Absätze → Sätze) und teilt erst innerhalb dieser rekursiv nach Token-Länge. Es wird **nicht mitten im Satz** geschnitten.

**Startwerte (im Spike empirisch zu kalibrieren):**

| Parameter         | Startwert                                        | Im Spike zu variieren |
| ----------------- | ------------------------------------------------ | --------------------- |
| Chunk-Grösse      | **512 Token**                                    | 256 / 512 / 1024      |
| Overlap           | **64 Token (~12,5 %)**                           | 0 % / 10 % / 20 %     |
| Splitting-Einheit | Token (tiktoken-kompatibel zum Embedding-Modell) | —                     |
| Grenzen-Priorität | Überschrift > Absatz > Satz                      | —                     |

Pro Chunk werden **Metadaten** mitgespeichert (Dokument-ID, Bereich, Quell-Überschrift/Seite, Position) — Grundlage für die spätere Quellenanzeige (US-01) und Metadata-Filterung.

### 2. Retrieval — Hybrid (Dense + Sparse) mit Reciprocal Rank Fusion

Pro Anfrage laufen **zwei Suchen parallel** und werden fusioniert:

- **Dense:** pgvector-Cosine-Similarity über den HNSW-Index (semantische Nähe).
- **Sparse:** PostgreSQL-Volltextsuche mit deutscher Konfiguration (`to_tsvector('german', …)`, GIN-Index) — fängt exakte Fachbegriffe/Akronyme, die Dense-Suche verfehlt.
- **Fusion:** **Reciprocal Rank Fusion (RRF)** kombiniert beide Ranglisten (`score = Σ 1/(k + rang)`, Start `k = 60`).

Ablauf: Kandidaten-`k = 20` je Suche abrufen → RRF-Fusion → **Schwellenwert-Gate** → Top-`n = 5` als Kontext an das LLM.

### 3. Schwellenwert-Gate — retrieval-seitiger Beitrag zur Reliability-NFA

Bevor überhaupt ein LLM-Aufruf erfolgt:

- Es muss **mindestens ein** Chunk eine Mindest-Similarity (Startwert **Cosine ≥ 0,35**, im Spike zu kalibrieren) überschreiten.
- Wird die Schwelle von **keinem** Chunk erreicht → **kein LLM-Aufruf**, direkte Antwort „**Weiss ich nicht**". Das ist der Hauptmechanismus gegen Halluzinationen bei Out-of-Corpus-Fragen (≥ 90 %-Ziel).
- Der Schwellenwert liegt in der `config`-Tabelle (ADR-003) — **ohne Deployment kalibrierbar**.

### 4. Grounding-Prompt-Kontrakt

Das LLM erhält ausschliesslich die `n` gefilterten Chunks als Kontext, mit der strikten Instruktion: **nur aus dem bereitgestellten Kontext antworten**, jede Aussage mit Quellen-Referenz belegen, und bei fehlender Deckung explizit „Weiss ich nicht" ausgeben. Damit ist die Retrieval-Ausgabe das einzige Wissensfundament der Antwort.

### 5. Re-Ranking — bewusst out-of-scope für den MVP

Ein Cross-Encoder-Re-Ranker ist der stärkste zusätzliche Präzisionshebel, würde aber entweder PyTorch ins Backend zurückholen (gegen ADR-005) oder einen weiteren Provider erfordern. Für den MVP wird darauf verzichtet; die Retrieval-Schnittstelle wird jedoch so geschnitten, dass ein Re-Ranking-Schritt **zwischen Fusion und Gate** ohne Architekturumbau nachgerüstet werden kann.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Hybrid-Retrieval adressiert die deutsche Fachsprache direkt: exakte Begriffe/Akronyme (Sparse) *und* semantische Nähe (Dense) — höhere Präzision als Dense-only.
- **+** Das Schwellenwert-Gate ist der wirksamste, billigste Hebel für die Reliability-NFA: Out-of-Corpus-Fragen werden ohne LLM-Aufruf abgewiesen (spart Tokens *und* verhindert Halluzination).
- **+** Kein zusätzlicher Service: Dense (pgvector) und Sparse (`tsvector`/GIN) laufen beide in PostgreSQL 17 — konsistent mit ADR-003.
- **+** Alle Schwellen-/Top-k-Werte in der `config`-Tabelle → empirische Kalibrierung im Spike ohne Deployment.
- **+** Struktur-bewusstes Chunking + Metadaten ermöglichen präzise Quellenangaben (US-01) statt willkürlicher Schnittgrenzen.

### Negative Konsequenzen

- **−** Hybrid-Retrieval ist komplexer als Dense-only: zweiter Index (GIN auf `tsvector`), Fusion-Logik, mehr Tuning-Parameter. Mitigation: RRF ist parameterarm (nur `k`); Sparse-Suche ist PostgreSQL-nativ.
- **−** Die Startwerte (512/64 Token, Cosine ≥ 0,35, k=20/n=5, RRF k=60) sind **Hypothesen**, keine validierten Werte — sie müssen im Spike gegen ein Eval-Dataset kalibriert werden. Ohne diese Kalibrierung ist die Reliability-NFA nicht garantiert.
- **−** Jeder Chunking-Parameter-Wechsel erzwingt vollständige Re-Indexierung (ADR-003/005). Mitigation: Parameter früh im Spike fixieren.
- **−** Kein Re-Ranking im MVP → bei sehr ähnlichen Chunks evtl. suboptimale Reihenfolge im Kontext. Akzeptiert für den Pilot; nachrüstbar (Punkt 5).
- **−** Ein zu hoher Schwellenwert erhöht fälschliche „Weiss ich nicht"-Antworten (Recall sinkt), ein zu tiefer lässt Halluzinationen durch (Precision sinkt) — der Trade-off muss messbasiert eingestellt werden (Abhängigkeit zur Eval-Strategie).

---

## Abgewogene Alternativen

| Alternative                                                                                | Warum verworfen                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Fixed-size Chunking (naiv, ohne Struktur)**                                              | Einfacher, aber schneidet mitten in Sätzen/Tabellen → zerrissener Kontext, schlechtere Embeddings und unbrauchbare Quellenausschnitte. Kein nennenswerter Implementierungsvorteil gegenüber struktur-bewusstem Splitting (beide via Standard-Splitter verfügbar). |
| **Semantic Chunking (Embedding-basierte Grenzen)**                                         | Theoretisch präzisere Grenzen, aber teuer (zusätzliche Embedding-Aufrufe schon beim Chunking) und schwerer reproduzierbar/debugbar. Für den MVP zu viel Aufwand; als Spike-Vergleichsoption nicht ausgeschlossen.                                                 |
| **Dense-only Retrieval (kein Sparse/RRF)**                                                 | Einfacher, ein Index. Verworfen, weil reine Vektorsuche exakte deutsche Fachbegriffe/Akronyme häufiger verfehlt — genau die Fälle, in denen Präzision für die Reliability-NFA zählt. Sparse ist in PostgreSQL ohnehin „gratis" verfügbar.                         |
| **Externes Hybrid-/Rerank-Framework (z. B. dedizierter Vector Store mit Built-in-Hybrid)** | Würde einen zweiten Service einführen (Widerspruch zu ADR-001/003). Kein Vorteil bei < 10 000 Chunks.                                                                                                                                                             |
| **Cross-Encoder-Re-Ranking im MVP**                                                        | Stärkster Präzisionshebel, aber bringt PyTorch ins Backend zurück (gegen ADR-005) oder einen weiteren Provider. Bewusst auf Post-MVP verschoben, Schnittstelle bleibt vorbereitet.                                                                                |
| **Kein Schwellenwert-Gate (immer Top-n an LLM, LLM entscheidet „weiss nicht")**            | Verlagert die gesamte Halluzinations-Abwehr ins LLM — unzuverlässig und teuer (LLM-Aufruf auch bei Out-of-Corpus). Das Gate ist der deterministische, prüfbare Schutz.                                                                                            |

---

## Offene Punkte / nächste Schritte

1. **Spike-Eval (Woche 1):** Eval-Dataset mit In-Corpus- und Out-of-Corpus-Fragen aufbauen; Chunking-Parameter, Schwellenwert und Top-k/n gegen die Reliability-NFA kalibrieren. (Abhängigkeit zur noch fehlenden Eval-Strategie.)
2. **ADR-008 (Konfidenz- & Unterdrückungspipeline):** Konfidenz-Berechnung und Self-Check als eigene Entscheidung — baut auf dem hier definierten Gate auf.
3. Parameter nach dem Spike als „Accepted" fixieren, *bevor* der Produktiv-Korpus indexiert wird.

---

*Abhängigkeiten: ADR-003 (pgvector + Postgres-FTS, Re-Indexierungskosten), ADR-004 (LLM für Grounding-Antwort), ADR-005 (Embedding-Modell/Dimension) · Folgt auf: offene kritische Lücke aus ADR-Review · Eröffnet: ADR-008 (Konfidenzpipeline)*
