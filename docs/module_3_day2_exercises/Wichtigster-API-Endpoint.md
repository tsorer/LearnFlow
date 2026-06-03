# Welcher der 5 MVP-Endpoints ist der wichtigste?

*Frage gestellt: 2026-06-03 · Kontext: LearnFlow MVP, US-01 + US-02*

---

## Frage

> Welcher dieser 5 API Endpoints ist der wichtigste?

---

## Antwort

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

*Christoph A. Amstutz, MD-PhD · Claude Sonnet 4.6 · 2026-06-03*
