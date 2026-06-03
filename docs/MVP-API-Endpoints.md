# Die 5 wichtigsten API-Endpoints für den LearnFlow MVP

*Frage gestellt: 2026-06-03 · Kontext: US-01 (Quellenbelegte Frage-Antwort) + US-02 (Unsichere Antworten erkennen)*

---

## Frage

> Unter Berücksichtigung von US-01 bis US-02: Welche 5 API-Endpoints sind für unseren MVP am wichtigsten?
> Für jeden Endpoint:
> - HTTP Methode (GET/POST/PUT/DELETE)
> - Path (/api/v1/...)
> - Was macht er?
> - Wer ruft ihn auf?

---

## Antwort

Basierend auf US-01 + US-02 als Kern (plus den unumgänglichen Voraussetzungen):

---

### 1. `POST /api/v1/auth/login`

**Was:** Prüft Username/Passwort, gibt HTTP-only Cookie mit JWT Access Token (15 min) + Refresh Token (7 d) zurück.

**Wer:** Browser (Lara & Stefan beim Login)

**Warum #1:** Ohne Auth sind alle anderen Endpoints unerreichbar — Voraussetzung für alles.

---

### 2. `POST /api/v1/query`

**Was:** Kernstück von US-01 + US-02. Nimmt Fragetext entgegen, führt Hybrid-Retrieval (Dense + Sparse/RRF) durch, prüft Schwellenwert-Gate, ruft LLM auf, gibt Antwort mit Quellen + Konfidenz-Metadaten als **SSE-Stream** zurück — oder direkt `"Weiss ich nicht"` wenn Gate nicht passiert.

Response-Struktur (grob):
```json
{
  "answer": "...",
  "confidence": { "score": 0.82, "band": "HIGH" },
  "suppressed": false,
  "sources": [
    { "doc_id": "...", "title": "...", "section": "...", "uploaded_at": "..." }
  ]
}
```

**Wer:** React Frontend (Lara)

**Warum #2:** Ist US-01 und US-02 in einem Endpoint.

---

### 3. `POST /api/v1/documents`

**Was:** Stefan lädt ein Dokument hoch (PDF/DOCX/MD, max 100 MB). Backend speichert Datei als `bytea`, legt einen pgqueuer-Job an → Background Worker chunked, embedded, indexiert. Gibt sofort `202 Accepted` + `job_id` zurück.

**Wer:** React Frontend (Stefan)

**Warum #3:** Ohne Korpus kein Retrieval — direkte Voraussetzung für US-01.

---

### 4. `GET /api/v1/documents/{doc_id}/content`

**Was:** Liefert das Originaldokument (als Base64/Binary Stream) damit der Browser es öffnen und den belegenden Abschnitt highlighten kann. Direkte Erfüllung des US-01-Akzeptanzkriteriums: *„Ein Klick auf Quellenangabe öffnet das Originaldokument und hebt den Abschnitt hervor."*

**Wer:** React Frontend (Lara, nach Klick auf Quellenlink)

**Warum #4:** Ohne diesen Endpoint ist das Quellenversprechen von US-01 technisch nicht einlösbar.

---

### 5. `POST /api/v1/feedback`

**Was:** Speichert 👍/👎, Kategorie und optionalen Freitext pseudonymisiert zur `answer_id`. Keine User-ID im Record — nur Session-Hash.

**Wer:** React Frontend (Lara)

**Warum #5:** US-03 ist Must-Have — ohne Feedback-Loop keine Qualitätskontrolle; Stefan sieht das Dashboard leer.

---

## Übersicht

| # | Methode | Path | Story |
|---|---|---|---|
| 1 | `POST` | `/api/v1/auth/login` | US-05 (Voraussetzung) |
| 2 | `POST` | `/api/v1/query` | **US-01 + US-02** |
| 3 | `POST` | `/api/v1/documents` | US-04 (Voraussetzung für #2) |
| 4 | `GET` | `/api/v1/documents/{doc_id}/content` | US-01 (Quellenhervorhebung) |
| 5 | `POST` | `/api/v1/feedback` | US-03 |

**Schlüsselbeobachtung:** Endpoint #2 trägt allein den gesamten Reliability-Stack (Retrieval-Gate → Konfidenz-Pipeline → Grounding-Check → LLM-Self-Check). Er ist der komplexeste Endpoint — und der einzige, der US-01 und US-02 gleichzeitig erfüllt.

---

*Christoph A. Amstutz, MD-PhD · Claude Sonnet 4.6 · 2026-06-03*
