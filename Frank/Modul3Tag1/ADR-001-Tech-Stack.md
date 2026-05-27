# ADR-001: Tech-Stack für LearnFlow MVP

**Datum:** 2026-05-27  
**Status:** Proposed  
**Autorinnen/Autoren:** Software-Architektur Team  

---

## Context

LearnFlow ist eine interne RAG-basierte Lernplattform, die Fragen in natürlicher Sprache mit quellenbasierten Antworten aus einem kuratierten Dokumentenkorpus beantwortet (US-01). Daneben werden Dokumenten-Upload (PDF, DOCX, Markdown, US-04), Konfidenzscoring (US-02), Feedback (US-03), KI-generierte Quizfragen (US-07/08) und eine passwortgeschützte Admin-Seite (US-11) benötigt.

Die bindenden Randbedingungen sind:

- **Budget:** 4 Entwicklerinnen/Entwickler × 80 h = **320 h gesamt**
- **Zeitrahmen:** 3 Monate MVP
- **Betrieb:** Interne Plattform; Datenschutz- und Compliance-Anforderungen des Unternehmens gelten
- **Team:** Generalistisches Entwicklungsteam, kein dediziertes ML-Ops-Profil
- **Kernfähigkeit:** Retrieval-Augmented Generation (RAG) — der gewählte Stack muss diesen Kern ohne Reibungsverluste unterstützen
- **Post-MVP:** SSO-Anbindung (Azure AD / SAML 2.0) ist geplant (US-05), aber explizit nicht im MVP-Scope

Die wichtigsten Entscheidungsdimensionen sind: Sprach-/Framework-Wahl für Backend und Frontend, Datenhaltung (relational + Vektoren), LLM-Integration sowie lokales Deployment.

Es wurden drei Alternativen gegenübergestellt:

| | **Option A (gewählt)** | Option B | Option C |
|---|---|---|---|
| Backend | Python + FastAPI | Node.js + Express | Java + Spring Boot |
| Frontend | React 18 + TypeScript + Vite | Next.js (Fullstack) | Vue 3 + TypeScript |
| DB (relational + Vektoren) | PostgreSQL 16 + pgvector | PostgreSQL + Qdrant | MongoDB Atlas |
| LLM-Integration | LangChain + Anthropic Claude API | LlamaIndex + OpenAI | Direktaufruf REST |
| Deployment | Docker Compose | Docker Compose | Kubernetes |

**Ausschlussgründe Option B:** Next.js-Fullstack vermischt Verantwortlichkeiten; Node.js-Ökosystem für RAG-Pipelines und Dokumentenverarbeitung (pypdf, python-docx) deutlich schwächer als Python. Qdrant als zweiter Infrastrukturbaustein erhöht Ops-Aufwand bei 320 h Gesamtbudget nicht vertretbar.

**Ausschlussgründe Option C:** Spring Boot-Startup-Overhead (Boilerplate, Build-Zeiten) und fehlendes natives Python-ML-Ökosystem machen Option C für ein KI-first-Produkt ungeeignet. Kubernetes übersteigt den Ops-Reifegrad für MVP.

---

## Decision

Wir verwenden folgenden Stack:

### Backend — Python 3.12 + FastAPI
Python ist der De-facto-Standard für LLM- und RAG-Anwendungen. FastAPI liefert automatische OpenAPI-Dokumentation, native async-Unterstützung und type-hint-basierte Validierung ohne nennenswerten Boilerplate. Alle relevanten Bibliotheken (LangChain, pypdf, python-docx, sentence-transformers, bcrypt) sind erstklassige Python-Pakete.

### Frontend — React 18 + TypeScript + Vite
Das Team kommt primär aus der .NET-Welt; reine Webentwicklung ist nicht der Schwerpunkt. React mit TypeScript wurde dennoch gegenüber Blazor/WASM und Vue bevorzugt, weil TypeScript konzeptuell C# nahesteht (statisches Typsystem, Interfaces, Generics) und .NET-Entwicklerinnen diesen Schritt erfahrungsgemäss schnell vollziehen. Die klare Grenze zwischen Python-Backend (OpenAPI-Spec) und React-Frontend ermöglicht parallele Entwicklung: Backend-lastige Teammitglieder bleiben im Python-Bereich, während maximal eine Person die React-UI verantwortet. Blazor WASM wurde ausgeschlossen, da es für Streaming-Antworten (LLM token-by-token) und Client-seitiges Highlighting von Quelltextpassagen (US-01) deutlich weniger ausgereifte Bibliotheken bietet als das React-Ökosystem. Vite hält die Build-Zeiten kurz.

### Datenbank — PostgreSQL 16 + pgvector-Extension
PostgreSQL übernimmt **beide** Datenhaltungsaufgaben: relationale Daten (Nutzer, Dokumente, Feedback, Quiz, Konfiguration) und Vektorembeddings via `pgvector`. Ein einziger Datenbankbaustein senkt Betriebskomplexität signifikant gegenüber einer Kombination aus RDBMS + dedizierter Vektordatenbank. Bei MVP-Datenmengen (ein Pilot-Bereich, überschaubare Dokumentenzahl) reicht pgvector für performante Cosine-Similarity-Suchen.

SQLite wurde explizit geprüft und ausgeschlossen: SQLite verfügt über keine produktionsreife Vektorerweiterunng (sqlite-vec ist experimentell, Stand 2026 nicht für Produktivbetrieb empfohlen). Eine SQLite-Kombination mit einer separaten Vektordatenbank würde zwei Datastores einführen und den einzigen strukturellen Vorteil von SQLite — minimaler Betriebsaufwand — zunichtemachen. Darüber hinaus sperrt SQLite bei gleichzeitigen Schreibzugriffen auf Dateiebene; die asynchrone Ingestion-Pipeline (Dokument-Upload → Chunking → Embedding, US-04) und gleichzeitige API-Anfragen würden zu Sperrkonflikten führen. PostgreSQL im Docker-Container verursacht keinen relevanten Mehraufwand gegenüber SQLite.

### LLM-Integration — LangChain + Azure OpenAI (EU)
LangChain abstrahiert RAG-Pipeline-Bausteine (Chunking, Embedding, Retrieval, Prompt-Templates) und ermöglicht spätere Modellwechsel ohne Architekturumbauten.

Für den LLM-Endpunkt wurden zwei Optionen bewertet:

| | **Azure OpenAI EU (gewählt)** | OpenAI API (direkt) |
|---|---|---|
| Datenresidenz | Europäische Rechenzentren (z. B. Switzerland North / West Europe) | US-Server; keine garantierte EU-Residenz |
| DSGVO / Datenschutz | Datenverarbeitung bleibt in der EU; kein Drittland-Transfer | Datentransfer in die USA; erfordert Standardvertragsklauseln |
| Unternehmensvertrag | Über bestehendes Azure-Enterprise-Agreement abrechenbar | Separater API-Vertrag notwendig |
| Modellverfügbarkeit | GPT-4o, GPT-4o-mini, text-embedding-3-small — dieselben Modelle wie direkte API | Gleiche Modelle, früher verfügbar |
| Latenz | Minimal höher durch EU-Routing | Geringfügig geringer bei US-Nutzern |
| LangChain-Integration | `AzureChatOpenAI` / `AzureOpenAIEmbeddings` — nativ unterstützt | `ChatOpenAI` — nativ unterstützt |

**Entscheid:** Azure OpenAI EU wird bevorzugt, weil LearnFlow interne Unternehmensdokumente verarbeitet. Deren Upload in einen US-Endpunkt ohne explizite Datenschutzprüfung würde gegen unternehmensweite Richtlinien verstossen. Die direkte OpenAI API bleibt als Entwicklungs-/Fallback-Option erlaubt (kein Produktivdaten-Upload in dieser Umgebung). LangChain kapselt den Endpunktwechsel hinter einer Konfigurationsvariable — kein Codeumbau erforderlich.

### Deployment — Docker Compose
Docker Compose fasst alle Services (FastAPI, React/Nginx, PostgreSQL) in einer einzigen `docker-compose.yml` zusammen. Reproduzierbare Umgebungen vom Laptop bis zum internen Server ohne Kubernetes-Overhead. Passt zur internen Infrastruktur und dem verfügbaren Ops-Know-how.

### Authentifizierung — JWT + bcrypt (MVP)
Für den MVP werden Accounts per DB-Script angelegt (US-05). JWT-Token mit kurzem Ablaufzeitraum (8 h) und bcrypt-gehashte Passwörter. Die FastAPI-Middleware-Schicht ist so gestaltet, dass sie im Post-MVP durch einen OAuth2/SAML-2.0-Flow gegen Azure AD ausgetauscht werden kann, ohne die restliche Applikationslogik anzufassen.

---

## Consequences

### Positiv

- **Kurze Time-to-Feature:** Python + FastAPI + LangChain sind für RAG-Anwendungen erprobt; Boilerplate ist minimal. Das ist kritisch bei 320 h Gesamtbudget.
- **Ökosystem-Alignment:** Alle MUST-User-Stories (US-01 bis US-05, US-11) sind mit diesem Stack ohne externe Abhängigkeitsprobleme umsetzbar.
- **Einheitliche Datenhaltung:** PostgreSQL + pgvector vermeidet Synchronisierungsprobleme zwischen RDBMS und Vektordatenbank.
- **Datenschutz-Compliance by Default:** Azure OpenAI EU hält Produktivdaten in europäischen Rechenzentren — kein Datentransfer in die USA, kein separates DSGVO-Gutachten für den LLM-Endpunkt erforderlich.
- **Modellunabhängigkeit:** LangChain-Abstraktion erlaubt Wechsel zwischen Azure OpenAI EU, direkter OpenAI API und lokalen Modellen per Konfigurationsvariable ohne Codeumbau.
- **SSO-Migrationspfad:** JWT-Middleware ist so strukturiert, dass der Wechsel auf SAML 2.0 / Azure AD (US-05 Post-MVP) ein isolierter Austausch der Auth-Schicht bleibt.

### Negativ / Risiken

- **React-Lernkurve für .NET-Team:** TypeScript ist konzeptuell C# ähnlich, React-Komponentenmodell und Frontend-Toolchain sind jedoch neu für das Team. Mitigierung: maximal eine Person verantwortet das Frontend, alle anderen bleiben im Python-Backend; OpenAPI-Spec definiert die saubere Grenze.
- **Zwei Sprachen im Stack:** Python (Backend) und TypeScript (Frontend) — Spezialisierung innerhalb des Teams wird durch die klare API-Grenze ermöglicht.
- **pgvector-Skalierungsgrenze:** Bei sehr grossen Dokumentenkorpora (> 1 Mio. Vektoren) stösst pgvector an Performance-Grenzen. Für den MVP mit einem Pilot-Bereich unkritisch; Migration auf eine dedizierte Vektordatenbank (z. B. Qdrant) ist jedoch ohne Datenverlust möglich, da das Datenmodell sauber getrennt ist.
- **LangChain-Abstraktionskosten:** LangChain fügt eine Indirektionsebene hinzu, die Debugging erschwert. Wenn die Abstraktion zum Hindernis wird, kann auf direkte Anthropic-API-Aufrufe zurückgefallen werden — die Schnittstellen bleiben stabil.
- **Keine Mobile-Optimierung:** React-SPA ist responsive, aber nicht als native App konzipiert. Für den internen MVP akzeptiert; Post-MVP-Entscheid separat zu treffen.
- **LLM-Kosten:** Azure OpenAI EU verursacht variable Betriebskosten pro Token. Azure-seitige Quotas und Rate-Limiting müssen vor Go-Live konfiguriert werden; Abrechnung läuft über bestehendes Azure-Enterprise-Agreement.

### Neutral / Folgeentscheide

- **ADR-002 (Embedding-Strategie):** Chunking-Grösse, Overlap, Embedding-Modell und Ähnlichkeitsmetrik werden in einem separaten ADR festgelegt (Tech-Spike erforderlich).
- **ADR-003 (Deployment-Umgebung):** Welcher interne Server, CI/CD-Pipeline, Secret-Management (Vault vs. Env-Files) — Folgearchitekturentscheid.
- US-14 (Antwort-Audit-Log) und US-15 (Mehrsprachigkeit) sind bewusst als WONT eingestuft und beeinflussen die Stackwahl nicht.

---

*Referenzdokumente: `LearnFlow_UserStories_v3.md` · `requirements_report_learnflow.md` · `LearnFlow_Plan_15Wochen.md`*
