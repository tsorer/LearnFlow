Ich möchte unsere Architekturentscheidung (Monolith vs. Modularer Monolith vs. Microservices) anhand eines strukturierten Entscheidungsrahmens bewerten.

Hier sind unsere Projektdaten:

- **Projekt:** LearnFlow — interne RAG-Lernplattform; neue Mitarbeitende stellen Fragen in natürlicher Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus. MVP: 1 Pilot-Bereich, < 30 Nutzer, Single Instance, Business Hours, Deadline 30. September 2026.
- **Team-Grösse:** 3 Devs (Frank, Niklaus, Reto), Backend-lastig, Code wird überwiegend KI-gestützt mit Claude Code generiert
- **Zeitrahmen bis MVP:** ~3 Monate, ~360 h total
- **Domain-Klarheit:** Teilweise klar — RAG-Pipeline definiert, Konfidenz-Scoring noch offen
- **Erwartete Nutzerzahl (Jahr 1):** < 30 (Pilot), danach ggf. 1–3 weitere Pilotbereiche
- **Grösster Skalierungs-Treiber:** Anzahl Dokumente im Korpus, nicht Concurrent Users
- **Unser ADR-001 sagt:** Modularer Monolith

Werte unser Projekt gegen diesen Entscheidungsrahmen aus:

| Kriterium | Monolith | Modularer Monolith | Microservices | Unsere Situation |
|---|---|---|---|---|
| Team-Grösse | 1–3 Devs | 2–8 Devs | > 10 Devs | ? |
| Zeitrahmen | < 6 Monate | 6–18 Monate | > 18 Monate | ? |
| Domain-Klarheit | Unbekannt | Teilweise klar | Sehr klar | ? |
| Skalierungsbedarf | Niedrig | Mittel | Hoch | ? |
| Deployment | Ein Mal | Pro Modul | Unabhängig | ? |

1. Fülle die Spalte "Unsere Situation" aus.
2. Welches Pattern gewinnt laut dieser Analyse — und stimmt das mit ADR-001 überein?
3. Gibt es Kriterien wo wir zwischen zwei Kategorien fallen? Wie gewichten wir diese?
