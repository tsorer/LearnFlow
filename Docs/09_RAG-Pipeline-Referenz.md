# RAG-Pipeline — Referenz: was wann wie berechnet wird

**Stand:** `main` (enthält T-38) plus T-54, 2026-09-02.

**Gegenstand:** wie aus einer Frage eine Antwort wird (Retrieval, Generierung, Konfidenz) und
wie ein Dokument überhaupt durchsuchbar wird (Indexierung). Alles andere — Rate-Limits, Auth,
Quiz, Reaper, Admin-Oberfläche — steht bewusst nicht hier.

Dieses Dokument ist **abgeleitet, nicht entscheidend**. Die Entscheide stehen in ADR-007
(Chunking/Retrieval) und ADR-008 (Konfidenz-Pipeline), der Vertrag nach aussen in
`src/backend/openapi.yaml`. Hier steht nur, was der Code heute tut — in seiner Reihenfolge, mit
den Variablen, die dabei gelesen werden. **Weicht dieses Dokument vom Code ab, ist dieses
Dokument falsch.** Verwiesen wird auf Datei und Funktion, nicht auf Zeilennummern — Zeilen
wandern, Funktionsnamen nicht.

---

## 1. Die Kette auf einen Blick

Neun Stellen können eine Anfrage beenden: acht liefern eine unterdrückte Antwort
(«Weiss ich nicht» mit `suppression_reason`), eine einen HTTP-Fehler.

```
POST /api/query
  │
  ├─ 0. Konfiguration lesen ......................... unlesbar ─► configuration_error
  │
  ├─ 1. Retrieval (dense + sparse + RRF) ............ Ausfall ──► HTTP 503 (keine Unterdrückung)
  │
  ├─ 2. Retrieval-Gate (Stufe 0) ................... kein Chunk ─► retrieval_gate
  │       any(score >= similarity_threshold)                      (kein LLM-Aufruf)
  │
  ├─ 3. Retrieval-Konfidenz (Stufe 1) .............. zu tief ───► retrieval_confidence
  │       result >= min_retrieval_confidence                      (kein LLM-Aufruf)
  │
  ├─ 4. Generierung ................ LLM-Aufruf 1 ── abgeschnitten ─► generation_truncated
  │                                                └ Sentinel ────► generation_refused
  │
  ├─ 5. Citation-Check (Stufe 2) ................... erfunden ──► citation_invalid
  │       valid && coverage >= min_citation_coverage  zu tief ──► citation_coverage
  │
  ├─ 6. Komposit + Band ............................ Band tief ─► confidence_band
  │       band_for(composite, medium, high)
  │
  ├─ 7. Self-Check (Stufe 3) ....... LLM-Aufruf 2 ── ungedeckt ─► self_check
  │       nur wenn low <= composite < high            (nur im Grenzband)
  │
  └─ Antwort + Quellen + Konfidenz
```

**Die Reihenfolge ist nicht die Stufennummer.** Stufe 2 läuft **vor** der Bandprüfung und vor
Stufe 3 — der Entscheid aus ADR-008, Nachtrag 2026-08-22 (T-26). Die erste Stufe, die nicht
passiert, unterdrückt; alle folgenden laufen nicht mehr.

**Ein Ausfall ist keine Unterdrückung.** Ein nicht erreichbarer Provider wird 503, nie
«Weiss ich nicht». Einen Ausfall als Produktverhalten auszuliefern würde ihn verstecken.

---

## 2. Alle Parameter

Vollständig für Retrieval, Generierung, Konfidenz und Indexierung — unabhängig davon, wo der
Wert steht.

**Spalte «Wo»** — wie man ihn ändert:

| Wert | Bedeutung |
|---|---|
| `UI` | `config`-Zeile, im Admin-Panel setzbar (⚙ Parameter), wirkt ab der nächsten Frage |
| `DB (nur SQL)` | `config`-Zeile, die Admin-API lehnt eine Änderung ab — nur per `psql` |
| `Env` | Umgebungsvariable, Deployment ohne Codeänderung |
| `Code · datei` | Konstante, nur per Commit, Review und Deployment |

**Spalte «Re-Index»** — ob eine Änderung eine vollständige Neuindexierung des Korpus verlangt
(§3). `–` heisst: wirkt sofort bzw. mit dem nächsten Deployment, ohne Nacharbeit am Bestand.

| Parameter | Wert | Wo | Re-Index | Wirkt auf |
|---|---|---|---|---|
| `similarity_threshold` | 0.35 | UI | – | Stufe 0 (Gate), Zähler der Evidenz-Dichte, Chunk-Färbung im Debug-Panel |
| `min_retrieval_confidence` | 0.40 | UI | – | Stufe 1 |
| `retrieval_top_k` | 20 | UI | – | Kandidaten **je** Suchart vor der Fusion |
| `context_top_n` | 5 | UI | – | Kontextgrösse, Nenner der Evidenz-Dichte, höchster gültiger Referenzindex |
| `rrf_k` | 60 | UI | – | Dämpfung der Rangfusion |
| `min_citation_coverage` | 0.50 | UI | – | Stufe 2 (Schwelle, nicht `valid`) |
| `confidence_threshold_medium` | 0.45 | UI | – | Bandgrenze «mittel»; darunter `confidence_band` |
| `confidence_threshold_high` | 0.75 | UI | – | Bandgrenze «hoch» |
| `self_check_band_low` | 0.45 | UI | – | Untergrenze Grenzband Stufe 3, inklusiv |
| `self_check_band_high` | 0.75 | UI | – | Obergrenze Grenzband Stufe 3, exklusiv |
| `chunk_size` | 512 | DB (nur SQL) | **ja** | Ziel-Chunkgrösse in Token |
| `chunk_overlap` | 64 | DB (nur SQL) | **ja** | Überlappung aufeinanderfolgender Chunks |
| `stale_days` | 90 | DB (nur SQL) | – | **nichts** — kein Reader in `app/` oder `worker/` (US-06 offen) |
| `llm_model` | `gpt-4o-mini` | Env | – | Generierung und Self-Check |
| `embed_model` | `text-embedding-3-small` | Env | **ja** | Query- und Chunk-Embeddings (ADR-005) |
| `embed_dimensions` | 1536 | Env | **ja** + Migration | Vektorlänge, muss zur Spalte passen |
| `litellm_base_url` / `_api_version` / `_api_key` | leer = OpenAI Direct | Env | – | Provider-Routing (ADR-004) |
| `WEIGHT_TOP_SCORE` | 0.5 | Code · `confidence.py` | – | Stufe-1-Score |
| `WEIGHT_MEAN_SCORE` | 0.3 | Code · `confidence.py` | – | Stufe-1-Score |
| `WEIGHT_EVIDENCE_DENSITY` | 0.2 | Code · `confidence.py` | – | Stufe-1-Score |
| `WEIGHT_RETRIEVAL_CONFIDENCE` | 0.5 | Code · `confidence.py` | – | Komposit |
| `WEIGHT_CITATION_COVERAGE` | 0.5 | Code · `confidence.py` | – | Komposit |
| `MIN_SEGMENT_WORDS` | 4 | Code · `confidence.py` | – | ab wann ein Segment als Aussage zählt — Nenner jeder Coverage |
| `SCORE_DIGITS` | 4 | Code · `confidence.py` | – | Rundung aller gespeicherten Scores |
| `MAX_TSQUERY_TERMS` | 10 | Code · `retrieval.py` | – | Terme der Sparse-Query |
| `MIN_TSQUERY_TERM_LENGTH` | 2 | Code · `retrieval.py` | – | kürzere Terme fallen aus der tsquery |
| `STOP_WORDS` | Liste | Code · `retrieval.py` | – | dito |
| `RANK_ABSENT` | 0 | Code · `retrieval.py` | – | Sentinel «nicht in dieser Rangliste» — kein Stellwert |
| `TEMPERATURE` | 0.0 | Code · `generation.py` | – | Reproduzierbarkeit (ADR-009) |
| `MAX_ANSWER_TOKENS` | 800 | Code · `generation.py` | – | Antwortlänge; wirkt direkt gegen `generation_truncated` |
| `TIMEOUT_SECONDS` | 30.0 | Code · `generation.py` | – | Zeitlimit LLM-Aufruf 1 |
| `MAX_RETRIES` | 0 | Code · `generation.py` | – | Wiederholungen LLM-Aufruf 1 |
| `REFUSAL_SENTINEL` | `WEISS_NICHT` | Code · `generation.py` | – | Prompt-Kontrakt, erkennt die Verweigerung |
| `TEMPERATURE` | 0.0 | Code · `self_check.py` | – | wie oben, für LLM-Aufruf 2 |
| `MAX_VERDICT_TOKENS` | 300 | Code · `self_check.py` | – | Urteilslänge |
| `TIMEOUT_SECONDS` | 20.0 | Code · `self_check.py` | – | Zeitlimit LLM-Aufruf 2 |
| `MAX_RETRIES` | 0 | Code · `self_check.py` | – | Wiederholungen LLM-Aufruf 2 |
| `VERDICT_COVERED` / `_UNCOVERED` | `GEDECKT` / `NICHT_GEDECKT` | Code · `self_check.py` | – | Sentinels des Urteils |
| `BATCH_SIZE` | 64 | Code · `embedding.py` | – | Texte je Embedding-Aufruf. ADR-006 leitet die Reaper-Frist daraus her — nicht allein ändern |
| `TIMEOUT_SECONDS` | 30.0 | Code · `embedding.py` | – | Zeitlimit je Embedding-Aufruf, gleiche Kopplung |
| `MAX_RETRIES` | 2 | Code · `embedding.py` | – | Wiederholungen je Embedding-Aufruf, gleiche Kopplung |
| `ENCODING_NAME` | `cl100k_base` | Code · `chunking.py` | **ja** | Tokenizer, gegen den `chunk_size` zählt |

Die zehn `UI`-Werte erscheinen zusätzlich als `debug.params_used` in jeder Antwort mit
Admin-Rolle, auch die von Stufen, die nicht liefen.

---

## 3. Was eine Änderung nach sich zieht

Nur eine Frage entscheidet über den Aufwand: **muss der Korpus neu indexiert werden?**

### 3.1 Nein (die grosse Mehrheit)

Alles mit `–` in der Tabelle. `UI`- und `DB`-Werte wirken ab der **nächsten Frage** — die
Konfiguration wird pro Request gelesen, kein Neustart nötig. `Env`- und `Code`-Werte brauchen
ein Deployment, danach ebenso sofort. Am Bestand ist nichts zu tun.

Das ist der Bereich, in dem kalibriert wird. Drei Werte lohnen dabei einen zweiten Blick, weil
sie **an mehr als einer Stelle** wirken und eine Änderung anders ausfällt als erwartet:

| Parameter | Wirkt zusätzlich |
|---|---|
| `context_top_n` | Nenner der Evidenz-Dichte (Stufe 1) — erhöhen senkt den Score, solange nicht entsprechend mehr Chunks über Schwelle liegen. Und: höchster gültiger Referenzindex — senken macht eine vorher gültige `[5]` zur erfundenen Referenz und damit zu `citation_invalid` |
| `similarity_threshold` | Zähler derselben Evidenz-Dichte, zusätzlich zum Gate |
| `confidence_threshold_medium` | ist nicht nur Bandgrenze, sondern die Unterdrückungsschwelle: was darunter liegt, wird gar nicht ausgeliefert |

**Bekannte Falle bei den Bändern:** `confidence_threshold_*` und `self_check_band_*` sind nicht
aneinander gekoppelt, und kein Constraint fängt das. `self_check_band_high` unterhalb von
`confidence_threshold_medium` schaltet Stufe 3 vollständig ab — sichtbar nur daran, dass die
`self_check`-Stufe im Debug-Panel bei jedem Score «ausserhalb des Grenzbands» meldet. Wer an
den Bändern dreht, prüft alle vier Werte zusammen.

### 3.2 Ja — fünf Werte

| Parameter | Warum |
|---|---|
| `chunk_size`, `chunk_overlap` | Bestehende Chunks behalten ihre Grenzen. Eine Änderung wirkt nur auf **neu** indexierte Dokumente — der Korpus wird gemischt, ohne dass es jemand sieht. Deshalb lehnt die Admin-API sie ab (T-42 will das ändern) |
| `ENCODING_NAME` | Bestimmt, wogegen `chunk_size` zählt; andere Tokenzählung heisst andere Chunkgrenzen |
| `embed_model` | **Alle** Embeddings müssen neu berechnet werden. Vektoren zweier Modelle sind nicht vergleichbar; ein gemischter Index liefert stillschweigend Unsinn, ohne Fehlermeldung |
| `embed_dimensions` | Muss zur Vektorspalte passen; ändern ohne Migration bricht schon das Schreiben der Chunks |

Reihenfolge immer: **Wert ändern → Korpus vollständig neu indexieren → erst dann messen.** Ein
Teil-Reindex ist schlimmer als keiner, weil das Ergebnis plausibel aussieht.

### 3.3 Eine Nebenwirkung, die niemanden aufhalten soll

Werte, die in die *Rechnung* eingehen statt nur in den Vergleich — `similarity_threshold`,
`context_top_n`, `retrieval_top_k`, `rrf_k` und die `WEIGHT_*` — verschieben die Skala von
`answers.confidence_score`. Zeilen von vor und nach einer Änderung messen dann nicht dasselbe.

Für den Pilotbetrieb ist das kein Hindernis: **hier wird optimiert, nicht archiviert.** Relevant
wird es nur, wenn jemand später eine Auswertung über gespeicherte `answers`-Zeilen fährt — dann
gilt der Zeitpunkt der letzten Parameteränderung als Beginn der Messreihe. Für Prod ist der Plan
ohnehin, die Parameter zu fixieren.

---

## 4. Indexierung — wie ein Dokument durchsuchbar wird

Im Worker, ausgelöst über pgqueuer beim Upload (ADR-006).

```
Upload (bytea, ≤ 10 MB)
  → Parsing (pypdf ≥ 6.16.2 / python-docx)
  → struktur-bewusstes Chunking     chunk_size / chunk_overlap, tiktoken cl100k_base
  → Embedding in Batches            embed_model, BATCH_SIZE
  → chunks + embedding + tsvector('german')
  → HNSW-Index (pgvector) + GIN (Volltext)
  → documents.status = 'available'
```

Jeder Chunk wird **zweimal** abgelegt: als Embedding-Vektor für die Dense-Suche und als
`tsvector` für die Sparse-Suche (§5.2). Die beiden Indizes darüber — HNSW und GIN — bedienen
je eine der beiden Suchen.

**Die Sparse-Hälfte steht und fällt mit der Textextraktion** (ADR-007, Präzisierung T-50). Die
Dense-Suche verkraftet ein zerrissenes Wort, die Sparse-Suche nicht: `hochr iskant` und
`hochriskant` sind für `to_tsvector('german', …)` verschiedene Tokens. Deshalb die Untergrenze
`pypdf >= 6.16.2` in `requirements.txt`, festgehalten von einem Minimal-PDF in
`tests/test_parsing.py`.

**Zwei Abkürzungslisten, absichtlich nicht geteilt.** `chunking.py` und `confidence.py` führen
je eine eigene. Beim Chunking ist ein Zeilenumbruch ein Layout-Artefakt des PDF und wird
ignoriert, beim Citation-Check ist er eine harte Segmentgrenze. Die Listen zu teilen würde eine
der beiden Stellen falsch machen.

---

## 5. Der Query-Pfad, Stufe für Stufe

### 5.1 Konfiguration lesen

`config.py::read_query_config` holt alle zehn Schwellen des Query-Pfads in **einem**
Round-Trip. Pro Anfrage, nicht beim Start — Schwellen müssen ohne Deployment und ohne Neustart
wirken (US-02, US-11).

| Fall | Verhalten |
|---|---|
| Zeile fehlt | Modul-Default (`DEFAULT_*` in `config.py`, deckungsgleich mit den Seeds) |
| Zeile da, unlesbar | `ConfigurationError` → `configuration_error`. Jemand hat etwas verlangt und es ging schief; eine lockerere Schwelle einzusetzen wäre fail-open (ADR-008, Nachtrag 2026-08-16) |
| Invertierte Bänder (`medium > high`) | ebenfalls `ConfigurationError` |

> **Achtung bei der Auswertung:** `configuration_error` liefert `suppressed = true`. Wer
> Unterdrückungen zählt, um eine Refusal-Rate zu bilden, zählt einen Betriebsfehler mit.

### 5.2 Retrieval — Hybrid + RRF (ADR-007)

#### Dense und Sparse — zwei Suchen, die verschiedene Fehler machen

Beide stellen Text als Zahlenvektor dar und suchen den nächstgelegenen. Der Unterschied steckt
in der Form des Vektors, und daher kommen auch die Namen:

| | **Dense** («dicht besetzt») | **Sparse** («dünn besetzt») |
|---|---|---|
| Vektor | 1536 Zahlen, praktisch alle ungleich null — erzeugt vom Embedding-Modell | eine Dimension je Wort des Vokabulars; ein Text belegt nur die Wörter, die er enthält, der Rest ist null |
| Misst | Nähe der **Bedeutung** | Übereinstimmung der **Wörter** |
| Umsetzung | pgvector, Cosine-Ähnlichkeit über HNSW-Index | Postgres-Volltextsuche, `tsvector`/GIN, Ranking mit `ts_rank_cd` |
| Findet | Umschreibungen, Synonyme, andere Formulierungen | exakte Fachbegriffe, Akronyme, seltene Wörter |
| Verfehlt | genau die seltenen Fachbegriffe | alles, was mit anderen Wörtern gesagt wird |

Ein **Embedding** ist die Zahlenrepräsentation, die ein Sprachmodell für einen Text erzeugt:
Texte mit ähnlicher Bedeutung liegen im Vektorraum nahe beieinander, auch wenn sie kein Wort
teilen. Deshalb findet die Dense-Suche zur Frage «Wer trägt die Verantwortung?» einen Abschnitt
über «Pflichten des Anbieters» — kein gemeinsames Stichwort, dieselbe Sache.

Ihre Schwäche ist die Spiegelseite davon: Ein seltener Fachbegriff kommt im Training kaum vor,
das Modell platziert ihn ungenau, und die Nähe wird unzuverlässig. Genau dort greift die
Sparse-Suche, die gar nichts versteht, sondern nur zählt, welche Wörter vorkommen — bei
deutschen Komposita wie «hochriskant» der zuverlässigere Weg. ADR-007 hat die Hybrid-Suche
deshalb eingeführt: nicht weil eine der beiden besser wäre, sondern weil sie sich in ihren
Fehlern ergänzen.

#### Warum fusioniert wird und nicht addiert

Die beiden Ergebnislisten lassen sich nicht verrechnen: eine Cosine-Ähnlichkeit liegt zwischen
0 und 1, ein `ts_rank_cd`-Wert ist nach oben offen und hängt vom Korpus ab. Sie auf eine
gemeinsame Skala zu bringen hiesse, ein Umrechnungsverhältnis zu erfinden.

**Reciprocal Rank Fusion** umgeht das, indem es die Werte gar nicht anfasst, sondern nur die
**Platzierung**: Jede Liste steuert `1 / (rrf_k + Rang)` bei, ein Chunk in beiden Listen bekommt
beide Summanden. Ein Treffer, den beide Suchen vorne haben, steigt dadurch nach oben; die
Konstante `rrf_k` dämpft, wie stark ein Spitzenplatz gegenüber einem Mittelfeldplatz zählt.

#### Ablauf

`retrieval.py::retrieve`:

1. **Dense:** Query-Embedding, Cosine über pgvector/HNSW → `score = 1 - (embedding <=> query)`,
   `LIMIT retrieval_top_k`. Kein Schwellenwert im `WHERE`: er wäre ein Post-Filter, der ins
   `LIMIT` schneidet.
2. **Sparse:** Postgres-Volltext `german` über `tsvector`/GIN, Stoppwörter entfernt, höchstens
   `MAX_TSQUERY_TERMS` Terme, dasselbe `LIMIT`. Selektiert dieselbe Cosine, damit ein reiner
   Sparse-Treffer für Stufe 0 und 1 einen Score hat.
3. **Fusion:** `rrf_score = Σ 1 / (rrf_k + rank)` über beide Ranglisten (`retrieval.py::fuse`).
   Ein Chunk, den nur eine Suche fand, trägt einen Summanden; sein Rang in der anderen Liste
   ist `RANK_ABSENT = 0` — ein reservierter Platzhalter, kein Rang. Echte Ränge zählen ab 1,
   die Null kann also nie mit einem echten kollidieren (mehr dazu in §5.5).
4. **Sortierung:** nach `(rrf_score, score)` absteigend. Der zweite Schlüssel, weil zwei Chunks
   denselben RRF-Wert haben können und die Reihenfolge sonst von der Dict-Iteration abhinge —
   derselbe Kontext käme zwischen zwei Läufen anders heraus.
5. **Kontext:** die ersten `context_top_n` Treffer.

Beide Suchen laufen sequenziell: eine `AsyncSession` hält eine asyncpg-Verbindung, und asyncpg
verbietet gleichzeitige Operationen darauf. «Parallel» in ADR-007 heisst, dass beide beitragen.

Sichtbar sind nur Chunks aus Dokumenten mit `status = 'available'` und passendem `area`, und
nur solche mit gesetztem `embedding`.

**Was das für die Reihenfolge heisst.** Bei `rrf_k = 60` schlägt ein Sparse-Treffer auf Rang 1
(`1/61 = 0.0164`) einen reinen Dense-Treffer auf Rang 3 (`1/63 = 0.0159`) — auch wenn dessen
Cosine deutlich höher ist. Ein Chunk mit 24 % Ähnlichkeit steht dann über einem mit 48 %, und
er kann im Kontext stehen, während der über der Schwelle weggeschnitten wird. Das ist kein
Fehler, sondern die Fusionslogik. Es ist auch der Grund, weshalb der erste Chunk im Kontext
nicht der ähnlichste sein muss — und weshalb Stufe 1 unten `max(scores)` nimmt statt
`scores[0]`.

**Nachvollziehbar ist das nur mit den Rängen** (T-54). `ChunkDebugInfo` führt deshalb neben
`dense_rank` auch `sparse_rank` und den `rrf_score` selbst — die drei Werte, welche die
Sortierung erzeugen —, dazu `chunk_id` und `document_id`, um eine Zeile einer Fussnote der
Antwort bzw. ihrem Dokument zuzuordnen. Alle fünf werden aus dem `RetrievalHit` übernommen, den
`fuse()` ohnehin gebaut hat; nachgerechnet wird nichts. Zuvor zeigte die Admin-Ansicht nur den
Dense-Rang, sortierte aber nach RRF — die Reihenfolge war von aussen nicht prüfbar.

Ein Detail, das dabei zählt: `rrf_score` wird auf sechs Stellen gerundet, nicht wie `score` auf
vier. Der Abstand zweier benachbarter RRF-Werte ist ~`1/(rrf_k + rang)²` und fällt ab etwa Rang
40 unter die vierte Stelle; `retrieval_top_k` lässt sich bis 100 stellen, und dort würde der
Schwanz der Kandidatenliste sonst auf einen Wert kollabieren.

### 5.3 Stufe 0 — Retrieval-Gate

```python
gate_passed = any(score >= similarity_threshold for score in context_scores)
```

Geprüft wird der **Kontext**, nicht die Kandidatenmenge (ADR-007, Präzisierung T-17). Die
umgekehrte Reihenfolge wäre fail-open: läge der einzige Chunk über Schwelle auf Fusionsrang 22,
passierte das Gate, und dem LLM gingen fünf Chunks zu, von denen keiner die Schwelle erreicht.

`>=`, nicht `>` — die konfigurierte Zahl ist der niedrigste Wert, der noch als Beleg zählt.
Kein Treffer → `retrieval_gate`, **ohne jeden LLM-Aufruf**: die billigste und wirksamste Stufe
der Kette.

Bei `retrieval_gate` werden auch **keine Quellen** zurückgegeben — die nächstliegenden Treffer
zu zeigen lüde dazu ein, sie als Antwort zu lesen. Bei `retrieval_confidence` bleiben sie: dort
sind die Quellen echt, nur die Grundlage ist dünn.

### 5.4 Stufe 1 — Retrieval-Konfidenz

`confidence.py::compute_retrieval_confidence`:

```python
top_score        = max(scores)
mean_score       = sum(scores) / len(scores)
evidence_density = min(count(score >= similarity_threshold) / context_top_n, 1.0)

result = 0.5 * top_score + 0.3 * mean_score + 0.2 * evidence_density
```

`result < min_retrieval_confidence` → `retrieval_confidence`, ebenfalls noch **vor** dem ersten
LLM-Aufruf.

**Warum `evidence_density` gegen `context_top_n` misst und nicht gegen die gefundenen Chunks:**
Drei gute Chunks von fünf geplanten sind eine schwächere Grundlage als fünf von fünf, und der
Wert soll das sagen. Die Deckelung auf 1.0 verhindert, dass ein erhöhtes `retrieval_top_k` ihn
aufbläht.

### 5.5 Generierung — der erste LLM-Aufruf

Erreicht nur, wenn Stufe 0 und 1 beide passiert sind. Der Grounding-Prompt (ADR-007) zwingt das
Modell, ausschliesslich aus dem Kontext zu antworten und jede Aussage mit `[n]` zu belegen; die
Kontext-Abschnitte werden ausdrücklich als Material, nicht als Anweisungen ausgewiesen.

- **`generation_truncated`** — `finish_reason == "length"`. Eine abgeschnittene Antwort ist
  nicht prüfbar: die Belege der fehlenden Sätze fehlen mit.
- **`generation_refused`** — Sentinel oder leere Antwort. Der Wortlaut des Modells wird
  verworfen und durch den standardisierten Text ersetzt: eine Verweigerung ist eine
  Unterdrückung, keine kurze Antwort.

#### Sentinel — warum das Modell ein Codewort ausgibt und keinen Satz

Ein **Sentinel** ist ein reservierter Wert, der «hier steht kein normaler Wert» bedeutet und mit
einem echten nicht verwechselt werden kann.

Antwortete das Modell im Freitext «Das lässt sich aus den Quellen nicht beantworten», wäre das
von einer kurzen, echten Antwort nicht sicher zu unterscheiden — man müsste den Text deuten,
also erneut raten, und zwar ausgerechnet an der Stelle, die existiert, weil die Pipeline dem
Modell nicht traut. Der Grounding-Prompt verlangt deshalb genau `WEISS_NICHT` und sonst nichts.
Damit wird aus einer Interpretationsfrage ein Zeichenvergleich, und die Verweigerung kann als
Unterdrückung behandelt werden — mit standardisiertem Text und `refinement_hint` — statt als
Antwort.

Geprüft wird entsprechend die Zeichenfolge, nicht der Sinn: bei der Generierung, ob die Antwort
mit `WEISS_NICHT` beginnt; beim Self-Check (§5.8), ob `GEDECKT` **allein** dasteht. Dort wird
`NICHT_GEDECKT` zuerst geprüft, und die Freigabe verlangt den blanken Sentinel — sonst ginge ein
«GEDECKTHEIT» im Fliesstext als Freigabe durch.

Dieselbe Idee ohne LLM ist `RANK_ABSENT = 0` (§5.2): ein Wert, der nie ein echter Rang sein
kann, statt eines `null`, das die Spec an dieser Stelle nicht zulässt. Weil er in der Antwort
mitfährt, hält `openapi.yaml` seit T-54 ausdrücklich fest, dass er «nicht gefunden» heisst und
nicht als Rang darzustellen ist — ein «#0» liest sich sonst wie ein Platz auf der Liste.

**Fail-closed gehört dazu.** Was sich nicht als Sentinel lesen lässt, gilt als der ungünstigere
Fall: eine leere Antwort zählt als Verweigerung, ein unlesbares Urteil als nicht bestanden. Ein
Sentinel, dessen Fehlen als «alles in Ordnung» gälte, wäre wertlos.

### 5.6 Stufe 2 — Citation-Check

Deterministisch, ohne LLM, auf dem generierten Text — `confidence.py::check_citations`.

**Segmentierung.** Zeilenumbruch = harte Grenze. Innerhalb einer Zeile Split an `.!?` +
Leerraum, mit Reparatur an Abkürzungen (`Art.`, `Abs.`, …) und am Buchstabenpaar (`z. B.`,
`d. h.`). Ein einzelner Grossbuchstabe vor dem Punkt ist **keine** Abkürzung — «Anhang A.»
beendet einen Satz. Listenmarker (`- `, `1. `) werden vorher entfernt.

**Zählbar** ist ein Segment ab `MIN_SEGMENT_WORDS` Wörtern, gezählt **nach** dem Entfernen der
Referenzen. Kürzere Fragmente («Fazit:», Überschriften) zählen weder als belegt noch als
unbelegt.

**Referenzen.** `[1]`, mehrfach `[1][2]`; `[1, 2]` toleriert; `[1-3]` **nicht** aufgelöst;
`[sic]` ignoriert. Gültig ist `1 <= n <= len(context)`, also `1..context_top_n`. Die Ziffernzahl
ist keine Grenze — `[2026]` ist so ungültig wie `[12]`.

```python
coverage        = covered / segments        # 0.0, wenn segments == 0
citation_passed = citation.valid and citation.coverage >= min_citation_coverage
```

Zwei Ausgänge, und die Reihenfolge ist bedeutsam:

- **`citation_invalid`** wird **zuerst** geprüft und ist **keine** Schwellenfrage. Eine Referenz
  auf einen nie gelieferten Chunk ist ein Modellfehler; auch perfekte Coverage macht ihn nicht
  auslieferbar.
- **`citation_coverage`** ist die Schwellenfrage, über `min_citation_coverage` kalibrierbar.

Ein Betreiber muss beide verschieden behandeln — das eine kalibriert man, das andere untersucht
man. Deshalb sind es zwei Werte im API-Vertrag.

### 5.7 Komposit und Band

`confidence.py::compute_composite` und `::band_for`:

```python
composite = 0.5 * retrieval_confidence + 0.5 * citation_coverage
composite = retrieval_confidence          # wenn Stufe 2 nicht lief

band = 'hoch'    wenn composite >= confidence_threshold_high
     = 'mittel'  wenn composite >= confidence_threshold_medium
     = 'niedrig' sonst
```

Eine nie gelaufene Stufe 2 als 0.0 einzurechnen würde jede Unterdrückung vor der Generierung
ins unterste Band drücken — für eine Messung, die nie stattgefunden hat.

`band == 'niedrig'` bei sonst passierten Stufen → `confidence_band`. **Das ist der Fall, für den
Defense-in-Depth existiert:** jede Einzelstufe war knapp akzeptabel, die Kombination trägt
trotzdem nicht. Das Komposit wird für jeden Ausgang berechnet, auch für unterdrückte Antworten.

`high` wird zuerst geprüft, damit `medium == high` das mittlere Band kollabieren lässt statt
einen Score in zwei Bändern zu erzeugen.

**Die Gewichte stehen im Code, nicht in `config`** (ADR-008, Nachtrag 2026-08-22). Eine Schwelle
justiert gegen eine feste Skala; eine Gewichtsänderung verschiebt die Skala selbst. Schwellen
sind Betrieb, Gewichte sind Modell.

### 5.8 Stufe 3 — Self-Check

Der zweite und letzte LLM-Aufruf und der einzige nicht-deterministische Teil der Kette. Läuft
**nur** im halboffenen Grenzband `self_check_band_low <= composite < self_check_band_high`
(`confidence.py::in_self_check_band`). Halboffen, weil ein Score genau auf `high` bereits klar
hohe Konfidenz ist. `low == high` ist ein leeres Band, also Stufe 3 bewusst abgeschaltet — so
wie `similarity_threshold = 0` Stufe 0 abschaltet.

Das Modell antwortet mit `GEDECKT` oder `NICHT_GEDECKT` plus den ungedeckten Aussagen im
Klartext — **ein Urteil, keine Zahl**. Ein Modell, das seine eigene Belegquote auf 78 %
beziffert, hat diese Zahl nicht gemessen, sondern erzeugt. Alles, was nicht als eines der beiden
Sentinels lesbar ist (leere Antwort, Prosa, eigene Schreibweise), gilt als **nicht** bestanden:
eine Prüfung, die sich nicht auswerten lässt, hat nicht stattgefunden.

---

## 6. Was gespeichert wird — und warum `NULL` nicht `0` ist

| Spalte in `answers` | Wann `NULL` | Warum die Unterscheidung zählt |
|---|---|---|
| `answer_text` | bei jeder Unterdrückung | Gespeichert wird, was ausgeliefert wurde; eine unterdrückte Antwort wurde es nicht |
| `citation_coverage` | wenn Stufe 2 nicht lief | Ein gespeichertes `0.0` hiesse «gemessen, nichts belegt» — ein anderer Sachverhalt als «nie gemessen» |
| `self_check_passed` | wenn Stufe 3 nicht lief (Normalfall) | Ein Default `false` liesse jede übersprungene Prüfung wie eine gescheiterte aussehen |
| `confidence_score` | — | Enthält seit T-23 das **Komposit**, nicht mehr die Retrieval-Konfidenz allein |

Im API-Feld `ConfidenceInfo.citation_coverage` fallen «nie gelaufen» und «0.0 gemessen» auf
`0.0` zusammen, weil die Spec das Feld nicht-nullable führt. Unterscheidbar bleiben sie nur über
`debug.stages` — und `debug` ist ausschliesslich für die Rolle `admin` gefüllt.

---

## 7. Was diese Zahlen nicht sind

**Alle Startwerte sind Hypothesen.** Coverage 0.50, die Gewichte, die Bandgrenzen 0.75/0.45 —
nichts davon ist gegen ein Eval-Dataset kalibriert. ADR-008 führt das als offenen Punkt 1,
ADR-009 hängt daran. Bis dahin garantieren sie die Reliability-NFA nicht, sie machen sie
plausibel.

**Die Bandgrenzen 0.75/0.45 sind nicht die 80 % / 50 % aus US-02.** Jene bezogen sich auf eine
LLM-Selbsteinschätzung und lassen sich nicht auf ein anders gebildetes Mass übertragen.

**Citation-Coverage misst Beleg-Form, nicht Korrektheit.** Ein Modell kann formal sauber
zitieren und trotzdem falsch schlussfolgern. Stufe 3 fängt einen Teil davon; der Rest ist
Restrisiko und über Eval zu messen.

**Bekannte Grenze:** Stufe 2 kann eine im Quelltext zitierte `[12]` nicht von einer erfundenen
Referenz unterscheiden. Gegen den Korpus geprüft — 0 Treffer in EU AI Act und SAMW-Leitfaden —
und bewusst nicht entschärft: jede Lockerung entschuldigt genau die Halluzination, die Stufe 2
fangen soll.

---

## 8. Abweichungen in den bestehenden Dokumenten

Gegen den Code geprüft. Bis zur Korrektur gilt die rechte Spalte.

| Fundstelle | Steht dort | Code |
|---|---|---|
| `06_Architecture-Draft.md`, «Retrieval (ADR-007)» | «Fusion → Gate → Top-`n`» | Fusion → Top-`n`-Schnitt → Gate (§5.2/5.3). ADR-007 trägt die Korrektur als Präzisierung T-17, `06` hat sie nicht übernommen |
| `04_ADR-008`, Haupttext «Komposit-Konfidenz & Anzeige» | «Gewichte in `config`» | Gewichte im Code (§2, §5.7). Der Nachtrag 2026-08-22 widerruft den Haupttext ausdrücklich — wer nur den Haupttext liest, liest es falsch |
| `04_ADR-008`, Nachtrag 2026-08-22 (T-37) | «elf `config`-Keys» | 15 Keys, 12 davon über die Admin-API schreibbar. Die Zahl stammt von vor Migration 0014 und 0017 |

Alle drei sind Korrekturen an den ADRs bzw. an `06` und gehören dorthin, nicht hierher.

---

## 9. Abgleich mit dem laufenden System

Die Tabelle in §2 nennt die **geseedeten Startwerte**; der laufende Stand kann abweichen:

```bash
docker exec src-db-1 psql -U learnflow -d learnflow -c "select key, value from config order by key;"
```

Am 2026-09-02 stand in der lokalen Entwicklungsdatenbank `min_citation_coverage = 0.28` statt
der geseedeten `0.50`. Wer eine Messung gegen diese DB fährt, misst dann nicht die dokumentierte
Pipeline — vor jeder Eval-Messung lohnt der Blick in die Tabelle.

---

## Fundstellen

| Thema | Datei |
|---|---|
| Stufen 0–2, Komposit, Bänder | `src/backend/app/services/confidence.py` |
| Orchestrierung, Unterdrückungsgründe | `src/backend/app/routers/query.py` |
| Schwellen-Reader, Defaults, Key-Listen | `src/backend/app/services/config.py` |
| Hybrid-Retrieval, RRF | `src/backend/app/services/retrieval.py` |
| Grounding-Prompt, Generierung | `src/backend/app/services/generation.py` |
| Stufe 3 | `src/backend/app/services/self_check.py` |
| Chunking, Embedding, Indexierung | `src/backend/app/services/chunking.py`, `embedding.py`, `src/backend/worker/main.py` |
| API-Vertrag, `suppression_reason`-Enum, `ChunkDebugInfo` | `src/backend/openapi.yaml` |
| Entscheide | `Docs/04_ADR-007_*`, `Docs/04_ADR-008_*` |
