# LearnFlow – Architektur & Entscheidungen

---

## System-Übersicht

```
[User]
  │  HTTP
  ▼
[Angular Frontend]
  │  REST API
  ▼
[FastAPI Backend]
  ├── RAG-Pipeline
  │     ├── Retrieval  → [Vector DB]
  │     ├── Generation → [Azure OpenAI EU]
  │     └── Confidence-Check
  └── Feedback-Speicherung → [DB / Datei]
```

---

## Architecture Decision Records (ADRs)

### ADR-001: Python (FastAPI) als Backend-Stack

**Entschieden:** tbd  
**Status:** Vorschlag

**Begründung:** Python ist die Standardsprache für RAG/LLM-Tooling. LangChain,
LlamaIndex und alle relevanten Vector-DB-Clients haben erstklassige Python-SDKs.
FastAPI liefert automatische OpenAPI-Docs und ist async-nativ.

**Alternativen:** Node.js/Express (bekannter für Angular-Devs, aber schlechteres LLM-Ökosystem)

---

### ADR-002: Azure OpenAI EU als LLM-Provider

**Entschieden:** tbd  
**Status:** Vorschlag

**Begründung:** Datenschutz (EU-Residency), bestehende Unternehmensverträge,
kein Vendor-Lock-in auf OpenAI.com.

---

### ADR-003: Vector DB (offen)

**Entschieden:** noch offen (Entscheidung in Sprint 0, Woche 1)  
**Status:** Offen

**Kandidaten:**
- **Chroma** – embedded, kein separater Service, ideal für Prototype
- **Qdrant** – production-ready, Docker-basiert, gute Python-SDK
- **pgvector** – wenn ohnehin PostgreSQL genutzt wird

**Kriterium:** Einfachstes Setup für Prototyp. Chroma bevorzugt bis Gegenbeweis.

---

### ADR-004: Kein echtes Auth im MVP

**Entschieden:** Ja  
**Status:** Beschlossen

**Begründung:** SSO/Auth kostet ~40 h. Budget nicht vorhanden. Demo läuft mit
hartcodiertem Demo-User. Konzept für echte Auth wird als Story im Backlog dokumentiert.

---

## Offene Entscheidungen (Sprint 0)

| Thema | Deadline | Verantwortlich |
|---|---|---|
| Vector DB Auswahl | Woche 1 | tbd |
| Frontend-State-Management (Service vs. NgRx) | Woche 1 | tbd |
| Deployment-Ziel (lokal / Cloud) | Woche 2 | tbd |
| Chunking-Strategie für Dokumente | Woche 2 | tbd |
