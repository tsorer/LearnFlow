# Lab L1 Teil 3 · Reality-Check Architecture Draft

*LearnFlow · Modul 3 Tag 2 · Reto Stucki · 2026-06-03*
*Quellen: Docs/06_Architecture-Draft.md · Docs/04_ADR-001 bis ADR-010 · Docs/01_UserStories.md*

---

## 1. Welche Teile unserer Architektur sind zu komplex für uns?

| Komponente                                          | Warum zu komplex                                                                                                                                                                                                                                                                    | Risiko                                                  |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **Mehrstufige Konfidenz-Pipeline (ADR-008)**        | 4 Stufen (Retrieval-Gate → Retrieval-Konfidenz → Citation-Check → LLM-Self-Check) mit gewichteter Komposit-Berechnung. Alle Schwellenwerte sind Hypothesen, die erst im Spike kalibriert werden. Gleichzeitig ist das der kritischste Pfad der gesamten Reliability-NFA.            | Spike schlägt fehl → MVP ohne belastbare Konfidenzwerte |
| **Hybrid-Retrieval + RRF (ADR-007)**                | Dense (pgvector HNSW) + Sparse (tsvector/GIN) + Reciprocal Rank Fusion mit `k=20` Kandidaten. Jeder Parameter (Chunk-Grösse, Overlap, Top-k, RRF-k, Similarity-Schwelle) ist ein Freiheitsgrad, der das Eval-Ergebnis beeinflusst — und alle müssen gleichzeitig kalibriert werden. | Parameterraum zu gross für 360 h                        |
| **Eval-Strategie mit CI-Regressionsgate (ADR-009)** | Gold-Dataset (80–100 Fragen, mit Stefan kuratiert) + RAGAS + CI-Gate der bei Halluzination > 0 % den Build bricht. Konzeptionell stark — aber der Aufwand für Dataset-Erstellung + RAGAS-Integration + CI-Konfiguration ist noch nicht geschätzt.                                   | Blockiert Sprint 1 wenn Spike länger als geplant dauert |
| **`bytea` vs. Large Object**                        | Offener Entscheid (Architecture-Draft markiert als Blocker). RAM/WAL-Verhalten für grosse PDFs ungeklärt — trifft die Datenarchitektur.                                                                                                                                             | Schema-Migration nötig wenn zu spät entschieden         |

---

## 2. Was würde ein Senior-Entwickler sofort vereinfachen?

**① Konfidenz-Pipeline: Phasenweise statt komplett**
Nicht alle 4 Stufen ab Tag 1. MVP-Minimum: Retrieval-Gate (Stufe 0) + Citation-Check (Stufe 2). Self-Check (Stufe 3) als Post-MVP-Feature — spart einen LLM-Aufruf pro Grenzfall und senkt die Latenz.

**② Hybrid-Retrieval: Dense-first, Hybrid später**
Statt sofort RRF-Fusion: In Sprint 1 nur Dense-Retrieval (pgvector HNSW). Sparse (tsvector) und RRF erst einführen wenn Eval zeigt, dass Dense allein nicht ausreicht. Vermeidet unnötige Komplexität wenn Dense für 80 % der Fälle reicht.

**③ Eval-Strategie: Manuell vor automatisiert**
Kein CI-Regressionsgate in Sprint 0. Erst ein manuell auswertbares Eval-Script, das lokal gegen das Gold-Dataset läuft. CI-Integration erst wenn die Metriken stabil sind — sonst wird der CI-Gate mehr Schmerz als Schutz.

**④ `bytea` entscheiden — jetzt**
Das ist ein Blocker (rot markiert im Architecture-Draft). PostgreSQL `bytea` funktioniert für PDFs ≤ 10 MB problemlos; für grössere Dateien ist `lo` (Large Object) oder externer Storage nötig. Entscheid: `bytea` für MVP (Limit: 10 MB, US-04 spezifiziert es), Large-Object-Migration als Post-MVP wenn nötig.

---

## 3. Was sollten wir aus dem MVP streichen damit es mit 360 h realistisch wird?

| Feature                                  | Empfehlung      | Begründung                                                                                                                                  |
| ---------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **LLM-Self-Check (Stufe 3, ADR-008)**    | ⏸ Post-MVP      | Zweiter LLM-Aufruf pro Grenzfall — erhöht Latenz und Kosten. Retrieval-Gate + Citation-Check decken das meiste ab.                          |
| **Quiz-Feature (US-07/08)**              | ⚠️ Scope-Check  | US-07/08 sind SHOULD in den User Stories — bei Budget-Druck erste Streichkandidaten. Kein Kern-MVP-Feature.                                 |
| **Quellenhervorhebung in PDFs (PDF.js)** | ⚠️ Vereinfachen | Architecture-Draft nennt es explizit als unterschätzten Scope. MVP-Alternative: Link auf Dokument + Seitenangabe statt inline Highlighting. |
| **CI-Regressionsgate (ADR-009)**         | ⏸ Sprint 1+     | Manuelle Eval-Scripts zuerst. CI-Gate nur wenn Sprint 0 Spike erfolgreich und Metriken stabil.                                              |
| **Stale-Content-Erkennung (US-06)**      | ⏸ Post-MVP      | E-Mail-Service noch ungeklärt (Architecture-Draft: offene Abhängigkeit). Kein Blocker für Kern-Q&A.                                         |

---

## 4. Ist unser Architecture Draft ehrlich — oder Wunschdenken?

**Ehrliche Einschätzung: Teils ehrlich, teils ambitioniert.**

**Was ehrlich ist:**

- Technologie-Stack (FastAPI, React, PostgreSQL, pgvector, pgqueuer) ist solide und für die Teamgrösse richtig dimensioniert. Keine Überarchitektur beim Stack.
- Modularer Monolith statt Microservices ist die richtige Entscheidung — das stimmt mit den Constraints überein.
- Die bekannten Risiken (PostgreSQL SPoF, pgqueuer Single-Threaded, Prompt-Injection) sind klar benannt.

**Was Wunschdenken ist:**

- **360 h für RAG + Eval + Quiz + Admin + Konfidenzpipeline** ist zu viel. Ein realistischer MVP müsste Stufung haben: Kern-Q&A zuerst, Eval und Quiz danach.
- **ADR-009 Eval-Strategie** ist architektonisch gut durchdacht — aber der Aufwand (Dataset mit Stefan erstellen, RAGAS konfigurieren, CI-Gate) ist nicht geschätzt. Das kann Sprint 0 komplett blockieren.
- **Alle Schwellenwerte als Hypothesen** (ADR-007/008) bedeutet: wir wissen nicht, ob Halluzinationsrate = 0 % mit unserem Stack erreichbar ist. Das ist kein Plan — das ist ein Tech Spike.

**Fazit:** Der Draft beschreibt was wir *wollen*, nicht was mit 360 h sicher *liefert*. Er braucht eine explizite Priorisierung: Was ist MVP-kritisch (läuft am 30. September)? Was ist Sprint 1+? Was ist Post-MVP?

---

## Was wir vereinfachen oder streichen

| Massnahme                                              | Impact                                            |
| ------------------------------------------------------ | ------------------------------------------------- |
| Self-Check (Stufe 3) → Post-MVP                        | -1 LLM-Aufruf pro Anfrage, weniger Latenzrisiko   |
| Dense-only Retrieval in Sprint 1, Hybrid ab Sprint 2   | Reduziert Parameterraum im Tech Spike erheblich   |
| Manuelle Eval vor CI-Gate                              | Sprint 0 bleibt fokussiert auf Kern-RAG           |
| `bytea` für MVP festlegen (10 MB Limit)                | Blocker sofort schliessen                         |
| Quiz (US-07/08) und Stale-Erkennung (US-06) → Post-MVP | Gibt ~60–80 h Budget zurück für Kern-Q&A-Qualität |
