# LearnFlow POC — Architektur-Entscheide & offene Fragen

*Erarbeitet Mai 2026 · Basis für Team-Review*

---

## Installation & Start

### Voraussetzungen
- Python 3.11+
- OpenAI API Key (platform.openai.com → API Keys → Create new secret key, Billing aufladen)

### Setup

```powershell
# 1. In den POC-Ordner wechseln
cd LearnFlow/poc

# 2. Virtuelle Umgebung erstellen und aktivieren
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Umgebungsvariablen konfigurieren
copy .env.example .env
# .env öffnen und OPENAI_API_KEY=sk-... eintragen
```

### Starten

```powershell
streamlit run app.py
```

Browser öffnet automatisch auf `http://localhost:8501`.

### Erster Test
1. Sidebar: Ein oder mehrere Dokumente hochladen (PDF, DOCX oder MD)
2. **Einlesen** klicken — Chunks-Zähler in der Sidebar steigt
3. Im Chat eine Frage zum Inhalt des Dokuments stellen
4. Konfidenz-Schwellenwert im Slider anpassen und Verhalten beobachten

### Daten zurücksetzen

```powershell
# Kompletten Vektor-Index löschen (Chroma)
Remove-Item -Recurse -Force chroma_db
```

---

## Was der POC heute macht

Streamlit-App mit RAG-Pipeline:

1. **Einlesen (Ingestion)**
   - Dokument (PDF / DOCX / MD) wird via Streamlit hochgeladen
   - `SimpleDirectoryReader` parst Text + Metadaten (Filename, Seitenzahl)
   - LlamaIndex teilt Text in Chunks (~1024 Tokens, 20 Token Overlap)
   - Jeder Chunk wird via OpenAI Embeddings API in einen Vektor (1536 Dimensionen) umgewandelt
   - Vektor + Originaltext + Metadaten werden in Chroma (lokal, Datei-basiert) gespeichert

2. **Frage stellen**
   - Die Frage wird ebenfalls in einen Vektor umgewandelt (gleiches Modell!)
   - Chroma sucht die 5 ähnlichsten Chunks via Kosinus-Ähnlichkeit
   - Confidence-Check: Score des besten Chunks wird gegen Schwellenwert geprüft
   - Die Top-3 Chunks werden als Kontext in den LLM-Prompt eingebaut
   - GPT-4o antwortet ausschliesslich auf Basis dieser Quellen

3. **Kontext zwischen Fragen**
   - Aktuell: **stateless** — jeder LLM-Call ist unabhängig
   - Streamlit zeigt die History nur zur Anzeige, sie wird nie ans LLM geschickt
   - Folgefragen ohne Kontext ("Und wer genehmigt ihn?") funktionieren nicht

---

## Stack-Entscheide

### LLM-Provider

| Option | Status | Begründung |
|---|---|---|
| **OpenAI API** | gewählt für POC | einfachstes Setup, beste Qualität, Niklaus hat Zugang |
| Azure OpenAI EU | geplant für Produktion | EU-Datenschutz, Unternehmens-SLA, selbe API |
| Claude (Anthropic) | möglich, aber hybrid | kein OpenAI-kompatibler Endpunkt, keine Embeddings-API → braucht zweiten Provider |
| Ollama / Llama lokal | möglich | configure()-Swap reicht; Qualität schlechter, GPU empfohlen |

**Wichtig:** OpenAI und Ollama sind beide über `http://localhost/v1` kompatibel (selbes API-Format). Claude ist es **nicht** — anderes HTTP-Format, LlamaIndex hat aber einen nativen Adapter.

### Vector Database

| Option | Bewertung |
|---|---|
| **Chroma** | gewählt für POC — embedded, keine Installation, Datei-basiert |
| pgvector | empfohlen für Produktion — PostgreSQL Extension, SQL + Vektoren in einer DB |
| sqlite-vec | interessant, aber noch jung (2024, v0.x) — noch nicht production-ready |
| LanceDB | file-basiert, produktionsreif, kein SQL |

**Kernunterschied Chroma vs. pgvector:**
- Chroma ist **nur** eine Vector DB — keine relationale Daten, kein SQL
- pgvector ist eine PostgreSQL-Extension — voller SQL-Stack + Vektoren in einer Instanz
- Für Produktion: pgvector bedeutet **eine** DB für alles (User, Dokumente, Feedback, Chunks)

### Relationale Daten im POC

Der POC hat **keine relationale DB** — kein User-Store, kein Dokument-Registry, keine Feedback-Tabelle.

Erweiterungsidee: **Chroma + SQLite parallel**
- Chroma → Vektoren/Chunks (wie heute)
- SQLite → relationale Daten (Dokument-Registry, Feedback, einfache User-Tabelle)
- Beide laufen als lokale Dateien, kein Server nötig
- Produktions-Migration: Chroma + SQLite → pgvector (alles in PostgreSQL)

---

## Bekannte Lücken im POC

### Duplikate beim Upload
Lädt man dasselbe Dokument zweimal hoch, liegen die Chunks doppelt in Chroma.

**Lösung:** Vor dem Einlesen alle Chunks mit gleichem Dateinamen löschen:
```python
existing_ids = collection.get(where={"filename": filename})["ids"]
if existing_ids:
    collection.delete(ids=existing_ids)
```
Chroma unterstützt das nativ via Metadaten-Filter. Entspricht US-04 AC (gleicher Dateiname = automatisch ersetzen).

### Kein Kontext zwischen Fragen (US-09)
Aktuell: `llm.complete(prompt)` — einfacher Text-Completion-Call ohne History.

Für US-09: `llm.chat(messages)` mit den letzten 3 Q&A-Paaren als `ChatMessage`-Liste.

### Confidence-Score ist ein Proxy
Der angezeigte Score ist die **Retrieval-Ähnlichkeit** (Kosinus-Score des besten Chunks), nicht ein echter "Belegungs-Anteil" wie US-02 ihn beschreibt. Der Self-Check-Mechanismus aus US-02 ist im POC nicht implementiert — und in den User Stories selbst auch noch nicht definiert.

---

## Skalierungs-Grenzen

| Komponente | Limit | Bemerkung |
|---|---|---|
| Streamlit Upload | 200 MB/Datei | konfigurierbar |
| OpenAI Embeddings | Rate Limit ~1M Tokens/min | bei vielen Docs in Batches hochladen |
| Chroma (Disk) | praktisch unbegrenzt | ~200 MB für 500 Dokumente |
| Chroma (Suche) | skaliert gut | HNSW-Index ab ~10k Chunks automatisch |

---

## Offene Fragen für den Team-Review

1. **Self-Check-Mechanismus (US-02):** Wie messen wir konkret den "Anteil belegter Aussagen"? Retrieval-Score als Proxy reicht das, oder brauchen wir einen separaten Verifikations-Step (z.B. zweiter LLM-Call der prüft ob die Antwort durch die Quellen gedeckt ist)?

2. **Embedding-Modell:** `text-embedding-3-small` oder `text-embedding-3-large`? Small ist günstiger, Large hat höhere Retrieval-Qualität. Wann ist der Unterschied spürbar?

3. **Chunk-Grösse:** LlamaIndex-Default ist 1024 Tokens. Für strukturierte Fach-Dokumente (z.B. Prozessbeschreibungen) könnte kleinere Chunk-Grösse + mehr Overlap bessere Präzision geben. Testen!

4. **sqlite-vec für Produktion?** Aktuell noch beta/v0.x — bis zum MVP-Deadline (Sep 2026) möglicherweise stabil. Wäre die eleganteste Lösung (SQL + Vektoren, eine Datei). Risiko: unbekanntes Verhalten bei Problemen.

5. **Kontext-Strategie (US-09):** Sliding window (immer letzte 3 Q&A-Paare) vs. semantische Auswahl der relevantesten vorherigen Paare?

6. **LLM-Provider für Produktion:** Azure OpenAI EU ist gesetzt — aber falls Anthropic einen EU-Endpunkt lanciert, wäre Claude eine Alternative. Claude hat kein Embedding-API → Hybrid-Setup nötig.

---

## Migrations-Pfad POC → Produktion

```
POC                          Produktion
─────────────────────────    ─────────────────────────
Streamlit                →   React + TypeScript (Vite)
FastAPI (fehlt)          →   FastAPI (Python)
OpenAI API               →   Azure OpenAI EU
LlamaIndex               →   LlamaIndex (bleibt)
Chroma (embedded)        →   pgvector (in PostgreSQL)
SQLite (geplant)         →   PostgreSQL (selbe Instanz)
─                        →   Docker Compose
─                        →   Auth (JWT → SSO post-MVP)
```

Der RAG-Kern (`rag.py`) bleibt strukturell gleich — nur `configure()` und der Vector-Store-Adapter ändern sich.
