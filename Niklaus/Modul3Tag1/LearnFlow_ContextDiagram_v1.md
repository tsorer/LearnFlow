# LearnFlow — C4 System Context Diagram v1
*Modul 3 Tag 1 · Mai 2026*

---

```mermaid
C4Context
    title System Context Diagram — LearnFlow

    Person(lara, "Lara", "Lernende / Junior Developer. Stellt Fragen, absolviert Quizze, gibt Feedback.")
    Person(stefan, "Stefan", "Bereichsverantwortlicher / Knowledge Owner. Verwaltet Lernkorpus und Quiz-Fragen.")
    Person(admin, "Admin", "Systemadministrator. Konfiguriert Parameter und verwaltet Accounts per DB-Script.")

    System(learnflow, "LearnFlow", "Interne Lernplattform mit RAG-basierter Frage-Antwort, Dokumentenverwaltung und Quiz-Modul.")

    System_Ext(llm, "LLM / Retrieval Service", "Sprachmodell fuer Antwort-Generierung, Konfidenz-Scoring und Quiz-Erstellung. (Provider noch offen)")
    System_Ext(idp, "Unternehmens-IdP", "SSO-Authentifizierung. (Post-MVP)")

    Rel(lara, learnflow, "Stellt Fragen, liest Antworten, absolviert Quizze, gibt Feedback", "Web")
    Rel(stefan, learnflow, "Laedt Dokumente hoch, validiert Quiz-Fragen, re-validiert Inhalte", "Web")
    Rel(admin, learnflow, "Konfiguriert Schwellenwerte, verwaltet Accounts", "Web")

    Rel(learnflow, llm, "Sendet Prompts, empfaengt Antworten und Konfidenz-Scores", "Abfrage")
    Rel(learnflow, idp, "Authentifiziert Nutzer via SSO (Post-MVP)", "SSO")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

---

## Legende

| Element | Beschreibung |
|---|---|
| **Lara** | Lernende — primäre Nutzerin der Q&A- und Quiz-Funktion |
| **Stefan** | Bereichsverantwortlicher — kuratiert den Wissenskorpus |
| **Admin** | Systemadministrator — konfiguriert Parameter, legt Accounts per DB-Script an |
| **LearnFlow** | Das zu bauende System (Scope dieser Arbeit) |
| **LLM / Retrieval Service** | Externer KI-Dienst für Antwort-Generierung und Quiz-Erstellung; Provider noch nicht entschieden (Risiko 3) |
| **Unternehmens-IdP** | Externer Identitätsprovider für SSO-Authentifizierung — explizit Post-MVP |


---

*Quelle: LearnFlow_Requirements_v1.md · Stand v1 — 2026-05-26*
