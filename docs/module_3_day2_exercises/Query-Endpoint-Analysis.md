# Query Endpoint: Bedeutung und OpenAPI 3.0 Spec

*Fragen gestellt: 2026-06-03 · Kontext: LearnFlow MVP, US-01 + US-02*

---

## Frage 1

> Welcher dieser 5 API Endpoints ist der wichtigste?

## Antwort 1

**`POST /api/v1/query`**

Kein anderer Endpoint kommt auch nur annähernd heran — und zwar aus drei Gründen:

**1. Er ist LearnFlow.**
Alle anderen Endpoints sind Infrastruktur (Login, Upload, Content-Abruf, Feedback). Dieser Endpoint *ist* das Produkt. Ohne ihn gibt es keine Lernplattform, nur eine Datei-Verwaltung.

**2. Er trägt allein den gesamten Reliability-Stack.**
In einem einzigen Request stecken vier Schichten:
```
Retrieval-Gate       → "Weiss ich nicht" ohne LLM-Aufruf
Konfidenz-Score      → Band HIGH / MEDIUM / LOW
Grounding-Check      → Coverage ≥ 50% sonst unterdrückt
LLM-Self-Check       → Grenzfälle
```
Das ist US-01 *und* US-02 gleichzeitig — kein anderer Endpoint bedient zwei Must-Have-Stories auf einmal.

**3. Er ist der einzige, der scheitern kann auf eine gefährliche Weise.**
- Login schlägt fehl → User sieht Fehlermeldung. Klar.
- Upload schlägt fehl → Job bleibt in Queue. Beherrschbar.
- **Query gibt eine halluzinierte Antwort zurück → Vertrauen in die Plattform ist dauerhaft beschädigt.**

Das ist der einzige Endpoint, bei dem ein Bug nicht nur ein technisches Problem ist, sondern das zentrale Qualitätsversprechen bricht.

> Wenn dieser Endpoint nicht korrekt funktioniert, hat LearnFlow kein Recht zu existieren.

---

## Frage 2

> Schreibe eine OpenAPI 3.0 Spec für diesen Endpoint:
> Inkludiere:
> - Path, Method, Summary, Description
> - Request Body mit Beispiel (JSON Schema)
> - Response 200 mit Beispiel
> - Response 400, 401, 404, 422 mit Fehlerbeschreibungen
> - Security: Bearer Token
>
> Format: YAML

## Antwort 2

```yaml
openapi: 3.0.3

info:
  title: LearnFlow API
  description: Interne RAG-Lernplattform — MVP (Pilot-Bereich, < 30 Nutzer)
  version: "1.0.0"
  contact:
    name: LearnFlow Team

servers:
  - url: http://localhost:8000/api/v1
    description: Lokale Entwicklung
  - url: https://learnflow.internal/api/v1
    description: Produktion

security:
  - bearerAuth: []

tags:
  - name: Query
    description: RAG-Kern — quellenbelegte Frage-Antwort (US-01 + US-02)

# ─────────────────────────────────────────────
paths:
  /query:
    post:
      operationId: postQuery
      tags: [Query]
      summary: Quellenbelegte Frage beantworten
      description: |
        Kernendpoint von LearnFlow. Führt in einem Request aus:
        Hybrid-Retrieval (Dense pgvector + Sparse tsvector, RRF-Fusion) →
        Schwellenwert-Gate → LLM-Generierung →
        mehrstufige Konfidenz-Pipeline (fail-closed).

        **Antwortformat:** Server-Sent Events (`text/event-stream`).
        Jede Zeile beginnt mit `data: ` gefolgt von einem JSON-Objekt.
        Das Feld `type` ist der Discriminator (vgl. ADR-002 Discriminated Union):

        | `type`      | Bedeutung                                              |
        |-------------|--------------------------------------------------------|
        | `delta`     | Nächstes Token der Antwort (Streaming)                 |
        | `metadata`  | Abschliessende Konfidenz-Daten + Quellen               |
        | `no_answer` | Gate nicht passiert — kein LLM-Aufruf                 |
        | `suppressed`| Antwort generiert, aber unterdrückt (Coverage < 50 %) |
        | `done`      | Stream-Ende                                            |

        **Reliability-Pipeline (fail-closed, ADR-008):**
        1. Retrieval-Gate: kein Chunk ≥ Similarity-Schwelle → `no_answer`
        2. Konfidenz-Score < konfiguriertem Schwellenwert → `no_answer`
        3. Grounding-Coverage < 50 % → `suppressed`
        4. LLM-Self-Check (Grenzfälle) → ggf. `suppressed`

        Alle Schwellenwerte sind ohne Code-Deployment änderbar (config-Tabelle, US-11).

      security:
        - bearerAuth: []

      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QueryRequest'
            example:
              question: "Was ist der Onboarding-Prozess für neue Entwickler?"
              conversation_history:
                - role: user
                  content: "Welche Tools werden bei uns eingesetzt?"
                - role: assistant
                  content: "Im Bereich werden hauptsächlich folgende Tools eingesetzt..."

      responses:

        '200':
          description: |
            SSE-Stream. Mögliche Event-Sequenzen:

            **Normale Antwort:** `delta`* → `metadata` → `done`
            **Keine Antwort:**   `no_answer` → `done`
            **Unterdrückt:**     `suppressed` → `done`
          content:
            text/event-stream:
              schema:
                $ref: '#/components/schemas/QueryStreamEvent'
              example: |
                data: {"type":"delta","text":"Der Onboarding-Prozess beginnt"}

                data: {"type":"delta","text":" mit einem zweitägigen Setup-Tag."}

                data: {"type":"metadata","answer_id":"ans_01jx4k2m9f","confidence":{"score":0.82,"band":"HIGH"},"suppressed":false,"sources":[{"doc_id":"doc_01jx","title":"Onboarding Guide 2026","section":"1.2 Setup-Tag","uploaded_at":"2026-05-15T08:00:00Z","chunk_id":"chunk_00042"}]}

                data: {"type":"done"}

        '400':
          description: |
            Ungültige Anfrage. Mögliche Ursachen:
            - `question` kürzer als 3 Zeichen (US-01 Akzeptanzkriterium)
            - `question` länger als 1.000 Zeichen (US-01 Akzeptanzkriterium)
            - `conversation_history` enthält mehr als 3 Q&A-Paare (> 6 Nachrichten)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                error: "INVALID_INPUT"
                message: "Die Frage muss zwischen 3 und 1000 Zeichen lang sein."
                field: "question"

        '401':
          description: |
            Nicht authentifiziert. Mögliche Ursachen:
            - Kein `Authorization: Bearer <token>`-Header vorhanden
            - JWT Access Token abgelaufen (TTL 15 Minuten)
            - JWT-Signatur ungültig oder manipuliert
            → Client soll POST /api/v1/auth/login (oder /auth/refresh) aufrufen.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                error: "UNAUTHORIZED"
                message: "JWT abgelaufen oder ungültig. Bitte erneut anmelden."

        '404':
          description: |
            Korpus nicht gefunden. Tritt auf, wenn für den Bereich des
            angemeldeten Nutzers noch kein Lernkorpus initialisiert wurde
            (kein einziges indexiertes Dokument vorhanden).
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                error: "CORPUS_NOT_FOUND"
                message: "Für diesen Bereich wurde noch kein Lernkorpus aufgebaut. Bitte zuerst Dokumente hochladen."

        '422':
          description: |
            Schema-Validierungsfehler (FastAPI / Pydantic).
            Pflichtfelder fehlen oder falscher Datentyp
            (z. B. `question` ist kein String, `role` hat ungültigen Wert).
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ValidationErrorResponse'
              example:
                detail:
                  - loc: ["body", "question"]
                    msg: "field required"
                    type: "value_error.missing"

# ─────────────────────────────────────────────
components:

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |
        JWT Access Token (HS256, TTL 15 min).
        Beziehen via `POST /api/v1/auth/login`.
        Format: `Authorization: Bearer <token>`

  schemas:

    # ── Request ──────────────────────────────
    QueryRequest:
      type: object
      required: [question]
      properties:
        question:
          type: string
          minLength: 3
          maxLength: 1000
          description: Frage in natürlicher Sprache (Deutsch).
          example: "Was ist der Onboarding-Prozess für neue Entwickler?"
        conversation_history:
          type: array
          maxItems: 6
          description: |
            Optionale Gesprächshistorie für Folgefragen (US-09).
            Maximal 3 vorherige Q&A-Paare = 6 Nachrichten.
            Älteste Paare werden bei Überschreitung verworfen (FIFO).
          items:
            $ref: '#/components/schemas/ConversationMessage'

    ConversationMessage:
      type: object
      required: [role, content]
      properties:
        role:
          type: string
          enum: [user, assistant]
        content:
          type: string
          maxLength: 2000

    # ── SSE Events (Discriminated Union) ─────
    QueryStreamEvent:
      description: |
        Discriminated Union — `type` bestimmt das Schema (ADR-002).
        Jedes Event wird als `data: <JSON>\n\n` gesendet.
      oneOf:
        - $ref: '#/components/schemas/DeltaEvent'
        - $ref: '#/components/schemas/MetadataEvent'
        - $ref: '#/components/schemas/NoAnswerEvent'
        - $ref: '#/components/schemas/SuppressedEvent'
        - $ref: '#/components/schemas/DoneEvent'
      discriminator:
        propertyName: type

    DeltaEvent:
      type: object
      required: [type, text]
      properties:
        type:
          type: string
          enum: [delta]
        text:
          type: string
          description: Nächstes Token oder Token-Chunk der Antwort.
          example: " beginnt mit einem zweitägigen Setup-Tag"

    MetadataEvent:
      type: object
      required: [type, answer_id, confidence, suppressed, sources]
      properties:
        type:
          type: string
          enum: [metadata]
        answer_id:
          type: string
          description: |
            UUID der Antwort.
            Wird als Referenz für `POST /api/v1/feedback` benötigt.
          example: "ans_01jx4k2m9f"
        confidence:
          $ref: '#/components/schemas/ConfidenceScore'
        suppressed:
          type: boolean
          description: |
            `true` wenn Antwort angezeigt wird, aber als
            "Eingeschränkt belegt" markiert ist (Grounding-Coverage 50–80 %).
        sources:
          type: array
          minItems: 1
          items:
            $ref: '#/components/schemas/Source'

    NoAnswerEvent:
      type: object
      required: [type, reason, suggestion]
      properties:
        type:
          type: string
          enum: [no_answer]
        reason:
          type: string
          enum: [out_of_corpus, low_confidence]
          description: |
            `out_of_corpus`  — kein Chunk überschritt die Similarity-Schwelle (Retrieval-Gate).
            `low_confidence` — Score unter konfiguriertem Konfidenz-Schwellenwert.
        suggestion:
          type: string
          description: Hinweis zur Präzisierung der Frage (US-02 Akzeptanzkriterium).
          example: "Versuche, einen konkreten Prozess oder ein Dokument zu nennen."

    SuppressedEvent:
      type: object
      required: [type, reason, confidence]
      properties:
        type:
          type: string
          enum: [suppressed]
        reason:
          type: string
          enum: [grounding_coverage_below_50, self_check_failed]
          description: |
            `grounding_coverage_below_50` — weniger als 50 % der Aussagen belegt.
            `self_check_failed`           — LLM-Self-Check hat ungedeckte Aussagen gefunden.
        confidence:
          $ref: '#/components/schemas/ConfidenceScore'

    DoneEvent:
      type: object
      required: [type]
      properties:
        type:
          type: string
          enum: [done]

    # ── Shared ───────────────────────────────
    ConfidenceScore:
      type: object
      required: [score, band]
      properties:
        score:
          type: number
          format: float
          minimum: 0.0
          maximum: 1.0
          description: |
            Komposit-Konfidenz aus Retrieval-Score und Grounding-Coverage.
            Konfigurierbare Schwellenwerte in der config-Tabelle (US-11).
          example: 0.82
        band:
          type: string
          enum: [HIGH, MEDIUM, LOW]
          description: |
            `HIGH`   — score ≥ oberer Schwellenwert (Default 0.75)
            `MEDIUM` — zwischen den Schwellenwerten
            `LOW`    — score < unterer Schwellenwert (Default 0.45)

    Source:
      type: object
      required: [doc_id, title, section, uploaded_at]
      properties:
        doc_id:
          type: string
          example: "doc_01jx4k2m"
        title:
          type: string
          description: Dokumenttitel oder Dateiname.
          example: "Onboarding Guide 2026"
        section:
          type: string
          description: Überschrift oder Seitenangabe des belegenden Chunks.
          example: "1.2 Setup-Tag"
        uploaded_at:
          type: string
          format: date-time
          example: "2026-05-15T08:00:00Z"
        chunk_id:
          type: string
          description: |
            Interne Chunk-ID — wird von `GET /api/v1/documents/{doc_id}/content`
            zur Quellenhervorhebung verwendet (US-01 Akzeptanzkriterium).
          example: "chunk_00042"

    # ── Errors ───────────────────────────────
    ErrorResponse:
      type: object
      required: [error, message]
      properties:
        error:
          type: string
          description: Maschinenlesbarer Fehlercode (SCREAMING_SNAKE_CASE).
          example: "INVALID_INPUT"
        message:
          type: string
          description: Menschenlesbare Fehlerbeschreibung (Deutsch).
          example: "Die Frage muss zwischen 3 und 1000 Zeichen lang sein."
        field:
          type: string
          description: Betroffenes Feld — nur bei Input-Validierungsfehlern gesetzt.
          example: "question"

    ValidationErrorResponse:
      type: object
      description: FastAPI / Pydantic Standard-Validierungsfehler (HTTP 422).
      properties:
        detail:
          type: array
          items:
            type: object
            properties:
              loc:
                type: array
                items:
                  type: string
                example: ["body", "question"]
              msg:
                type: string
                example: "field required"
              type:
                type: string
                example: "value_error.missing"
```

---

**Drei Designentscheide in der Spec:**

1. **Discriminated Union** für SSE-Events — direkt aus ADR-002: `type` als Discriminator, `oneOf` mit fünf Schemas. FastAPI kann das mit Pydantic `Literal` 1:1 abbilden.

2. **`answer_id` im `metadata`-Event** — damit `POST /api/v1/feedback` einen sauberen Referenzpunkt hat, ohne die Antwort neu identifizieren zu müssen.

3. **`chunk_id` in `Source`** — Brücke zu `GET /documents/{doc_id}/content` für das Highlighting-Akzeptanzkriterium von US-01.

---

*Christoph A. Amstutz, MD-PhD · Claude Sonnet 4.6 · 2026-06-03*
