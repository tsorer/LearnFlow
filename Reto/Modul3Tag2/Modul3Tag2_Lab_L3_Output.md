# Lab L3 · Pitch-Vorbereitung
*LearnFlow · Modul 3 Tag 2 · Reto Stucki · 2026-06-03*

---

## 1. Der stärkste 1-Satz

> **LearnFlow ersetzt das «Frag mal Stefan»-Problem: neue Mitarbeitende erhalten quellenbelegte Antworten auf Fachfragen — sofort, ohne jemanden zu unterbrechen.**

---

## 2. Die 3 Fragen die ein CTO sofort stellen würde

**① «Wie verhindert ihr Halluzinationen?»**
Mehrstufige Fail-Closed-Pipeline (ADR-008): Retrieval-Gate → Konfidenz-Score → Citation-Check. Keine Antwort ohne valide Quellenreferenz. Lieber «Weiss ich nicht» als eine falsche Antwort.

**② «Was passiert wenn eure Datenbank ausfällt?»**
PostgreSQL ist Single Point of Failure — kein Replica, kein Backup definiert. Das ist unser grösstes bekanntes Risiko. Mitigation: Backup vor Pilot-Start als harte Voraussetzung, Business-Hours-Only-Betrieb reduziert Exposure.

**③ «Wie skaliert ihr über 30 Nutzer hinaus?»**
MVP ist bewusst Single Instance. Stateless-Design (ADR-001) hält die Tür offen: horizontales Scaling des API Servers ist ohne Redesign möglich. PostgreSQL-Read-Replica als nächster Schritt.

---

## 3. Antwort auf «Warum nicht Microservices?»

> 3 Devs, 360 h, < 30 Nutzer. Microservices kosten uns schätzungsweise +80–120 h nur für Infrastruktur — Service Discovery, separate CI/CD-Pipelines, verteiltes Tracing. Das ist Budget das wir in RAG-Qualität stecken. Modularer Monolith mit import-linter als CI-Gate gibt uns die Wartbarkeit ohne den Ops-Overhead. Netflix und Uber haben auch als Monolith angefangen.

---

## 4. Antwort auf «Was ist euer grösstes Risiko?»

> PostgreSQL ohne Replica und ohne definierten Backup-Prozess. Wir haben es benannt, wir verstecken es nicht. Mitigation: Backup-Strategie und nächtliche Snapshots sind Voraussetzung vor dem ersten Pilot-User — nicht nach MVP. Zweites Risiko: Prompt-Injection ist architektonisch noch nicht adressiert.

---

## 5. Was wir NICHT sagen sollten

- Alle 10 ADRs der Reihe nach aufzählen
- Technische Details (pgvector HNSW, RRF-Fusion, Matryoshka-Dimensionen)
- «Wir haben noch nicht entschieden ob...» (öffnet Diskussionen die Zeit fressen)
- Den Unterschied zwischen OpenAI Direct und Azure OpenAI EU erklären
- Offene Punkte als Liste vorlesen — nur die eine wichtigste nennen
