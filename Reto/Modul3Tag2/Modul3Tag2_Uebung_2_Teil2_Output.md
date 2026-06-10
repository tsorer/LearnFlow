# Ü2 Teil 2 · OpenAPI Spec — POST /api/v1/questions
*LearnFlow · Modul 3 Tag 2 · Reto Stucki · 2026-06-03*
*Quelle: Docs/01_UserStories.md (US-01, US-02) · Docs/04_ADR-002_Backend-Frontend-Stack.md*

---

```yaml
openapi: "3.0.3"
info:
  title: LearnFlow API
  version: "1.0.0"
  description: >
    Interne RAG-Lernplattform — neue Mitarbeitende stellen Fragen in natürlicher
    Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus.

servers:
  - url: https://learnflow.internal/api/v1

security:
  - bearerAuth: []

paths:
  /questions:
    post:
      summary: Frage stellen und Antwort streamen
      description: >
        Nimmt eine Frage in natürlicher Sprache entgegen und führt die vollständige
        RAG-Pipeline aus (Embedding → Retrieval → Konfidenz-Check → LLM-Generierung).
        Die Antwort wird token-by-token via Server-Sent Events (SSE) gestreamt.
        Unterschreitet der Konfidenz-Score den konfigurierten Schwellenwert, wird
        keine inhaltliche Antwort generiert (US-02: Halluzinationsrate = 0 %).
      operationId: postQuestion
      tags:
        - Questions
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/QuestionRequest"
            example:
              question: "Wie wird ein neuer Deployment-Prozess in unserem System ausgelöst?"
              corpus_area: "engineering"
      responses:
        "200":
          description: >
            SSE-Stream mit der generierten Antwort und Quellenbelegen.
            Content-Type: text/event-stream.
            Jedes Event hat ein `event`-Feld (token | sources | confidence | done | error)
            und ein `data`-Feld (JSON).
          content:
            text/event-stream:
              schema:
                type: string
                description: Server-Sent Events stream
              examples:
                token_event:
                  summary: Einzelnes Token während Streaming
                  value: |
                    event: token
                    data: {"token": "Der Deployment-Prozess wird"}

                sources_event:
                  summary: Quellenbelege am Ende des Streams
                  value: |
                    event: sources
                    data: {
                      "sources": [
                        {
                          "document_title": "Deployment-Handbuch v3.2",
                          "section": "Abschnitt 4.1 — Release-Prozess",
                          "validated_at": "2026-04-15",
                          "document_id": "doc_a1b2c3"
                        }
                      ]
                    }

                confidence_event:
                  summary: Konfidenz-Score
                  value: |
                    event: confidence
                    data: {"score": 0.87, "grounded_ratio": 0.92}

                done_event:
                  summary: Stream abgeschlossen
                  value: |
                    event: done
                    data: {"answer_id": "ans_x9y8z7"}

        "400":
          description: >
            Ungültige Anfrage — Frage zu kurz (< 3 Zeichen), zu lang (> 1000 Zeichen)
            oder fehlendes Pflichtfeld. Validierung erfolgt clientseitig und serverseitig (US-01).
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
              example:
                error: "validation_error"
                message: "Frage muss zwischen 3 und 1000 Zeichen lang sein."
                field: "question"

        "401":
          description: Kein gültiger Bearer Token oder Token abgelaufen (JWT, 8 h Gültigkeit).
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
              example:
                error: "unauthorized"
                message: "Authentifizierung erforderlich. Bitte erneut anmelden."

        "404":
          description: Corpus-Bereich nicht gefunden oder keine Dokumente im Bereich vorhanden.
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
              example:
                error: "corpus_not_found"
                message: "Für den Bereich 'engineering' sind keine Dokumente im Korpus verfügbar."

        "422":
          description: >
            Konfidenz-Score unter Schwellenwert — das System verfügt über keine
            belastbaren Informationen zur gestellten Frage (US-02: Out-of-Corpus).
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/LowConfidenceResponse"
              example:
                error: "low_confidence"
                message: "Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden."
                hint: "Versuche, einen konkreten Prozess oder ein Dokument zu nennen."
                confidence_score: 0.21

        "503":
          description: LLM- oder Retrieval-Service nicht erreichbar — kontrollierte Degradation, kein Fallback-Text (US-01).
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
              example:
                error: "service_unavailable"
                message: "Der KI-Dienst ist momentan nicht erreichbar. Bitte versuche es in wenigen Minuten erneut."

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: JWT-Token aus POST /auth/login, Gültigkeit 8 Stunden.

  schemas:
    QuestionRequest:
      type: object
      required:
        - question
      properties:
        question:
          type: string
          minLength: 3
          maxLength: 1000
          description: Frage in natürlicher Sprache (deutsch oder englisch).
          example: "Wie wird ein neuer Deployment-Prozess in unserem System ausgelöst?"
        corpus_area:
          type: string
          description: Pilot-Bereich (MVP hardcoded; Post-MVP konfigurierbar).
          example: "engineering"

    ErrorResponse:
      type: object
      required:
        - error
        - message
      properties:
        error:
          type: string
          description: Maschinenlesbarer Fehlercode.
        message:
          type: string
          description: Menschenlesbare Fehlerbeschreibung (deutsch).
        field:
          type: string
          description: Betroffenes Feld bei Validierungsfehlern (optional).

    LowConfidenceResponse:
      type: object
      required:
        - error
        - message
      properties:
        error:
          type: string
          example: "low_confidence"
        message:
          type: string
          description: Standardisierte "Weiss ich nicht"-Antwort.
        hint:
          type: string
          description: Kontextueller Hinweis zur Fragenverbesserung (US-02).
        confidence_score:
          type: number
          format: float
          minimum: 0
          maximum: 1
          description: Tatsächlicher Score für Debugging und Admin-Auswertung.
```

---

## Überraschungen / Offene Punkte

- **SSE + OpenAPI:** OpenAPI 3.0 hat keine native Unterstützung für SSE-Streams — die `text/event-stream` Response ist eine pragmatische Lösung, aber nicht formal validierbar. AsyncAPI wäre die sauberere Lösung für Event-Streams.
- **422 vs. 200 für Low-Confidence:** Diskussionswürdig. Alternativ könnte Low-Confidence als `200` mit `answered: false` zurückkommen — konsistenter für das Frontend, aber semantisch weniger sauber.
- **`corpus_area` im MVP hardcoded:** Das Feld ist bereits im Schema, aber für den Pilot irrelevant. Vorbereitung für Post-MVP Multi-Bereich.
- **`answer_id` im `done`-Event:** Ermöglicht das spätere Verknüpfen von Feedback (US-03, `POST /answers/{answer_id}/feedback`) ohne separaten State im Frontend.
