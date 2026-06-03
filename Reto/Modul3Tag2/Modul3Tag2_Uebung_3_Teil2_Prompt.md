Unser Projekt: LearnFlow — interne RAG-Lernplattform. Architektur: Modularer Monolith (FastAPI + React + PostgreSQL + pgvector). Team: 3 Devs, ~360 h total. Lese-Operationen dominieren (Nutzer fragen häufig, schreiben selten). User Stories: Docs/01_UserStories.md.

Bewerte CQRS (Command Query Responsibility Segregation) für unser Projekt:

1. Haben wir Endpoints die 100x häufiger gelesen als geschrieben werden? (Beispiele?)
2. Wie komplex wäre die CQRS-Implementierung für uns — konkret?
3. Brauchen wir CQRS jetzt, später oder nie — begründe für unser spezifisches Szenario (< 30 Nutzer MVP, dann ggf. Scale-out).
4. Wenn nicht jetzt: Wie designen wir heute so, dass CQRS später nachrüstbar ist?
