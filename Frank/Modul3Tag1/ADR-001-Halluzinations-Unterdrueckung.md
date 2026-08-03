# ADR-001: Mehrschichtiger Halluzinations-Unterdrückungsmechanismus

| | |
|---|---|
| **Status** | Accepted |
| **Datum** | 2026-05-27 |
| **Projekt** | LearnFlow — interne RAG-basierte Lernplattform |

---

## Context

LearnFlow beantwortet Fachfragen auf Basis eines kuratierten Dokumenten-Korpus mittels RAG (Retrieval-Augmented Generation). Ein LLM kann prinzipbedingt Antworten erzeugen, die plausibel klingen, aber inhaltlich falsch sind — auch wenn eine Quellenreferenz im Retrieval-Schritt gefunden wurde. Eine einzige halluzinierte Antwort, die von einer Nutzerin als korrekt akzeptiert wird, beschädigt das Vertrauen in die Plattform nachhaltig und kann den Piloten zum Scheitern bringen.

Zusätzlich ist das System von einem externen LLM-Service abhängig (Azure OpenAI / Ollama). Quota-Überschreitung, Timeouts oder Serviceausfall dürfen nie zu einer generierten Fallback-Antwort führen — das System muss in diesen Fällen kontrolliert degradieren.

Die Kernfrage lautet: Wie reduzieren wir das Halluzinationsrisiko auf ein messbares, akzeptiertes Minimum — und wie stellen wir sicher, dass das System bei Unsicherheit schweigt statt rät?

**Wichtige Einschränkung:** Kein architektonischer Mechanismus kann Halluzinationen vollständig eliminieren. Stufe 1 und 2 messen Retrieval-Qualität — ob das gefundene Dokument semantisch ähnlich zur Frage ist. Sie garantieren nicht, dass der LLM daraus eine korrekte Antwort ableitet. Das Ziel ist eine nachweislich niedrige und messbare Fehlerrate, nicht die Zusicherung von Null-Fehlern.

## Decision

Wir implementieren einen **zweistufigen Unterdrückungsmechanismus** mit anschliessendem **Faithfulness-Check** als dritter Stufe. Jede Stufe kann die Antwort stoppen — keine Stufe darf übersprungen werden.

```
Stufe 1 · Quellenprüfung
  Bedingung : Mindestens ein Dokument mit ausreichender Ähnlichkeit im Korpus gefunden
  Reaktion  : Kein Treffer → "Keine passende Quelle gefunden" — kein LLM-Aufruf
  Hinweis   : Verhindert LLM-Aufruf bei völlig thremdfremden Fragen (günstigste Stufe)

Stufe 2 · Konfidenz-Score (Retrieval)
  Bedingung : Retrieval-Score des besten Treffers ≥ konfiguriertem Schwellenwert
  Reaktion  : Score < Schwellenwert → "Ich weiss es nicht sicher" — kein LLM-Aufruf
  Hinweis   : Schwellenwert in der Datenbank, nicht im Code — kalibrierbar ohne Deployment
              Kalibrierung ist modell- und korpusspezifisch (→ Tech Spike pro Provider)

Stufe 3 · Faithfulness-Check
  Bedingung : Generierte Antwort wird durch die gefundenen Quelltexte gestützt
  Methode   : Separater LLM-Prompt prüft explizit: "Ist diese Antwort vollständig durch
              die folgenden Textausschnitte belegbar? Ja / Nein + Begründung"
  Reaktion  : Nicht belegbar → Antwort wird unterdrückt, Quelltexte werden direkt angezeigt
  Hinweis   : Bewusste Entscheidung gegen LLM-Self-Check (Selbsteinschätzung korreliert
              nachweislich schlecht mit tatsächlicher Korrektheit)
```

**Warum Faithfulness-Check statt LLM-Self-Check:**
Ein LLM der halluziniert, halluziniert auch bei der Selbsteinschätzung seiner Antwortqualität. Der Faithfulness-Check fragt dagegen eine überprüfbare Frage: Ist jede Aussage in der Antwort durch einen der vorgelegten Textausschnitte belegbar? Diese Frage ist präziser und robuster als "Wie sicher bist du dir?"

**Performance-Implikation:** Stufe 3 erfordert einen zweiten LLM-Aufruf und addiert Latenz. Das 10s @ p95 SLA muss im Tech Spike unter Einbezug beider Aufrufe gemessen werden. Falls die kombinierte Latenz das SLA verletzt, wird Stufe 3 asynchron nach der Antwort ausgeführt — mit nachträglicher Markierung unsicherer Antworten.

Für den LLM-Service-Ausfall gilt zusätzlich ein **Circuit Breaker**: Bei Timeout, HTTP 5xx oder erschöpfter Quota wird eine Fehlermeldung ausgegeben — niemals ein generierter Text.

## Consequences

**Positiv**

- Halluzinationsrisiko auf ein messbares Minimum reduziert — nachweisbar durch Evaluationsdataset (Out-of-Corpus ≥ 90 % "Weiss ich nicht")
- Faithfulness-Check ist robuster als Self-Check: prüft Belegbarkeit statt Selbsteinschätzung
- Jede Stufe unabhängig kalibrierbar, messbar und durch Testfälle abdeckbar
- Schwellenwert in der Datenbank: Stefan kann ohne Deployment kalibrieren
- Erweiterbar: weitere Prüfstufen addierbar ohne Redesign
- Kontrolliertes Degradationsverhalten bei externem Serviceausfall

**Negativ**

- Höhere False-Negative-Rate: System sagt häufiger "Weiss ich nicht", auch bei korrekten Grenzfällen
- Stufe 3 (zweiter LLM-Aufruf) erhöht Latenz — 10s @ p95 SLA muss im Tech Spike validiert werden
- Schwellenwerte sind modell- und korpusspezifisch: bei Provider-Wechsel (→ ADR-003) ist Neukalibrierung zwingend
- Kein architektonischer Mechanismus garantiert Halluzinationsrate = 0 % — das muss im Nutzer-Onboarding kommuniziert werden
- Circuit Breaker muss separat implementiert und getestet werden
