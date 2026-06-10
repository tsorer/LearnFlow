# L2 · Teil 2 · ADR für Pattern-Entscheidung
*LearnFlow · Modul 3 Tag 1 · Reto Stucki · 2026-05-31*

---

## ADR-002: Architektur-Pattern — Modularer Monolith

| Feld | Inhalt |
|---|---|
| **Titel** | ADR-002: Modularer Monolith als Architektur-Pattern für LearnFlow MVP |
| **Status** | Entschieden — 2026-05-31 |

---

### Kontext — Warum müssen wir zwischen Monolith / Microservices entscheiden?

LearnFlow besteht aus klar abgrenzbaren Domains: RAG-Pipeline, Dokumentverwaltung, Quiz, Auth und Admin-Konfiguration. Diese Domains könnten prinzipiell als separate Services deployed werden — was jedoch die Frage aufwirft, ob der Trennungsaufwand für unser Team und unseren Zeitrahmen gerechtfertigt ist.

Rahmenbedingungen die die Entscheidung erzwingen:
- 3 Devs · 360–480 h Budget · MVP bis 30. September 2026
- Domain noch nicht vollständig verstanden: Konfidenz-Scoring undefiniert, Chunking-Strategie offen
- MVP: 1 Pilot-Bereich, < 30 Nutzer, Single Instance — kein Skalierungsdruck heute
- Post-MVP: Multi-Bereich, SSO-Anbindung, potenziell mehr Nutzer — Architektur muss Ausbau ermöglichen ohne Redesign

Ein reiner Monolith erschwert die spätere Extraktion von Modulen. Microservices erzeugen heute Overhead (Service Discovery, Inter-Service-Auth, Distributed Tracing) der das Budget für Kernfunktionen aufbraucht bevor US-01 fertig ist.

---

### Entscheidung

**Wir wählen den Modularen Monolith**, weil er die C2-Grenzen (4 Container) als physische Schnitte beibehält und den API Server intern in saubere Module aufteilt — ohne den Overhead verteilter Services.

Konkrete Umsetzung:
- API Server (FastAPI) wird intern modular strukturiert: `rag/`, `documents/`, `quiz/`, `auth/`, `admin/`
- Modul-Grenzen werden durch klare Import-Regeln und keine zirkulären Abhängigkeiten durchgesetzt
- Background Worker bleibt als separater Prozess (pgqueuer) — die physische Trennung ist dort gerechtfertigt weil asynchrones Dokument-Processing den 5-Minuten-SLA erfordert und nicht im Request-Cycle des API Servers laufen darf
- Diese Hybridform (Modularer Monolith + separater Worker) ist bewusst dokumentiert und kein Einstieg in Microservices

---

### Positive Konsequenzen

- Keine Service Discovery, kein API Gateway, kein Inter-Service-Auth — volle Entwicklungszeit fliesst in Fachfunktionen
- Saubere Modul-Grenzen heute ermöglichen spätere Service-Extraktion (z. B. RAG-Service bei Multi-Bereich-Ausbau) ohne vollständigen Umbau
- Ein Deployment-Artefakt — Docker Compose bleibt überschaubar
- Self-Check-Mechanismus und Konfidenz-Pipeline können als kombinierte Operation innerhalb eines Prozesses implementiert werden — kein verteiltes Transaktionsproblem
- Testbarkeit: jedes Modul isoliert testbar, kein Service-Mocking zwischen Prozessen nötig

---

### Negative Konsequenzen

- Disziplin bei Modul-Grenzen ist Team-Vereinbarung, kein technischer Zwang — Grenzen können im Zeitdruck erodieren («mal schnell direkt importieren»)
- Skalierung einzelner Komponenten (z. B. nur Embedding-Generierung skalieren) nicht möglich ohne Umbau
- Background Worker als Ausnahme vom Modularen Monolith muss bewusst gepflegt werden — Risiko dass weitere «Ausnahmen» hinzukommen und die Architektur unkontrolliert fragmentiert
- Post-MVP Service-Extraktion erfordert Refactoring — kein Zero-Cost-Upgrade zu Microservices

---

*Quellen: [Modul3Tag1_Lab_L2_Teil1_Output.md](Modul3Tag1_Lab_L2_Teil1_Output.md) · [Docs/05_C4-C2_Container.md](../../Docs/05_C4-C2_Container.md) · [Docs/02_Requirements.md](../../Docs/02_Requirements.md)*
