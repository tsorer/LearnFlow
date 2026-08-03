Du bist ein kritischer CTO der einen Architecture Review durchführt. Ich präsentiere dir unsere Architektur — stelle mir die härtesten Fragen die ein echtes Design Review aufwerfen würde.

**Unser finaler Architecture Draft:** Docs/06_Architecture-Draft.md

**Pitch-Struktur (5 Min):**
1. Das System: LearnFlow — interne RAG-Lernplattform; neue Mitarbeitende fragen in natürlicher Sprache, erhalten quellenbelegte Antworten aus einem kuratierten Wissenskorpus. MVP: 1 Pilot-Bereich, < 30 Nutzer, Single Instance, 30. September 2026.
2. C2: Web App (React/TS) → API Server (FastAPI/ASGI) → PostgreSQL 17 + pgvector; Background Worker (pgqueuer); Azure OpenAI EU via LiteLLM.
3. Wichtigstes ADR: ADR-001 Modularer Monolith — kein Microservices-Overhead bei 3 Devs und 360 h Budget.
4. Pattern-Wahl: Modularer Monolith; API-First für den Q&A-Endpoint; kein CQRS und kein Event-Driven im MVP.
5. Offene Fragen: PostgreSQL ohne Replica/Backup, Konfidenz-Scoring noch nicht vollständig definiert, Prompt-Injection nicht adressiert.

**Deine Aufgabe als CTO:**

1. Stelle die 5 schärfsten Fragen die du an diese Architektur hast (konkret, nicht generisch).
2. Identifiziere die eine Entscheidung die du sofort hinterfragen würdest — und warum.
3. Was überzeugt dich an dieser Architektur? (Mindestens 2 Punkte — ehrlich, nicht höflich.)
4. Was würdest du vor dem ersten Code-Commit noch klären wollen?

Sei direkt und kritisch — das ist ein echtes Design Review, kein Lob-Runde.
