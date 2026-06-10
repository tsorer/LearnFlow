# Ü2 Teil 1 · Top-5 API Endpoints — LearnFlow
*LearnFlow · Modul 3 Tag 2 · Reto Stucki · 2026-06-03*
*Quellen: Docs/01_UserStories.md · Docs/06_Architecture-Draft.md*

---

## Top-5 API Endpoints für den MVP

| # | Method | Path | Aufrufer | Was macht er? |
|---|---|---|---|---|
| 1 | `POST` | `/api/v1/questions` | Web App (Lara) | Nimmt eine Frage in natürlicher Sprache entgegen, führt die RAG-Pipeline aus (Retrieval → Konfidenz-Check → LLM-Generierung) und streamt die Antwort mit Quellenbelegen via SSE zurück. Kernstück des Systems — direkt aus US-01, US-02. |
| 2 | `POST` | `/api/v1/documents` | Web App (Stefan) | Upload eines Dokuments (PDF, .docx, Markdown) in den Lernkorpus. Startet asynchron den Background Worker (pgqueuer) für Chunking + Embedding. Antwort sofort; Dokument verfügbar nach ≤ 5 Min (US-04). |
| 3 | `POST` | `/api/v1/auth/login` | Web App (alle) | Username/Passwort-Login, gibt JWT zurück (8 h Gültigkeit). Basis für jede weitere Anfrage — RBAC (User / Admin) via Token-Claims (US-05). |
| 4 | `POST` | `/api/v1/answers/{answer_id}/feedback` | Web App (Lara) | Speichert Feedback (👍/👎 + Kategorie + optionaler Freitext) pseudonymisiert zur Antwort. Input für Stefan-Dashboard und Qualitätssicherung (US-03). |
| 5 | `GET` | `/api/v1/documents` | Web App (Stefan) | Listet alle Dokumente des Pilot-Bereichs mit Zeitstempel, Status (processing / ready / error) und Dateiname. Grundlage für Korpus-Verwaltung (US-04). |

---

## Begründung der Reihenfolge

`POST /questions` ist der kritischste Endpoint: er trägt die gesamte RAG-Pipeline, das SSE-Streaming, den Konfidenz-Check und die Quellenverknüpfung — alle MUST-User-Stories hängen daran. Ohne ihn gibt es kein Produkt.

`POST /documents` ist der zweite Kernpfad: ohne Korpus-Upload keine Inhalte, keine Antworten.

`POST /auth/login` ist technisch simpel, aber Gate für alles andere — kein JWT, kein Zugriff.

`POST /feedback` ist klein, aber MVP-Pflicht (US-03 ist MUST) und kritisch für Qualitätssicherung im Pilot.

`GET /documents` schliesst den Verwaltungskreis für Stefan und ist Voraussetzung für US-04 (Löschen, Versionsersatz).
