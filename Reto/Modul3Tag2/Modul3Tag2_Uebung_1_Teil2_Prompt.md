Wir haben uns für Modularen Monolith entschieden (ADR-001: Docs/04_ADR-001_Architekturstil.md).

Unser Kontext:
- Projekt: LearnFlow — interne RAG-Lernplattform; neue Mitarbeitende stellen Fragen in natürlicher Sprache und erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus. MVP: 1 Pilot-Bereich, < 30 Nutzer, Single Instance, Business Hours, Deadline 30. September 2026.
- Team: 3 Devs (Frank, Niklaus, Reto), Backend-lastig, ~360 h total
- Stack: Python 3.13 / FastAPI + React 18 / TypeScript + PostgreSQL + pgvector
- Top-3 QAs: Reliability · Security · Maintainability (Details: Docs/03_QualityAttributes.md)

Spiele jetzt den Advocatus Diaboli:

1. Warum ist diese Entscheidung für uns FALSCH?
2. Was werden wir in 6 Monaten bereuen?
3. Welches Pattern wäre ehrlich gesagt besser — und warum?
4. Was müssen wir tun damit unsere Wahl wirklich funktioniert?
