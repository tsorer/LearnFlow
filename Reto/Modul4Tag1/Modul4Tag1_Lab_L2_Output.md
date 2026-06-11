# LearnFlow — Sprint Planning (Lab L2)

*Modul 4 Tag 1 · Juni 2026*

---

> Backlog-Grundlage: `Reto/Modul4Tag1/Modul4Tag1_Lab_L1_Output.md`
> Team & Constraints: `Docs/02_Requirements.md`

---

## Rahmenbedingungen

- **Sprint-Länge:** 1 Woche
- **Sprint 0:** Infrastruktur — kein Feature-Code
- **Sprint 1:** Erster Feature-Sprint auf bereitem Fundament

---

## Sprint 0 — Infrastruktur (1 Woche)

**Ziel:** Lokale Entwicklungsumgebung und CI laufen; API-Kontrakt steht.

| ID   | Task                                                                       | SP  | Bereich |
| ---- | -------------------------------------------------------------------------- | --- | ------- |
| T-01 | Docker Compose Setup: Services api, worker, db, frontend mit Health-Checks | 3   | DevOps  |
| T-02 | CI Pipeline: lint, type-check, pytest/vitest, build                        | 3   | DevOps  |
| T-03 | OpenAPI Spec Grundgerüst: alle Endpunkte aus US-01–05 als Stubs            | 3   | Backend |

**Sprint-0-Summe: 9 SP**

Reihenfolge: T-01 zuerst (T-02 braucht laufende Container), T-03 parallel zu T-01 möglich.

---

## Sprint 1 — Auth-Fundament (1 Woche)

**Ziel:** DB-Schema steht; erster Nutzer kann sich einloggen und ein JWT erhalten.

| ID   | Task                                                                                         | SP  | Bereich |
| ---- | -------------------------------------------------------------------------------------------- | --- | ------- |
| T-04 | DB-Schema Initial-Migration: Tabellen users, documents, chunks, embeddings, feedback, config | 3   | DB      |
| T-06 | FastAPI: POST /auth/login → JWT (8h), bcrypt-Passwort-Prüfung                                | 5   | Backend |

**Sprint-1-Summe: 8 SP**

Reihenfolge: T-04 → T-06 (T-06 braucht users-Tabelle).

---

## Was bewusst NICHT in Sprint 0/1

| Ausschluss                   | Begründung                                                                    |
| ---------------------------- | ----------------------------------------------------------------------------- |
| T-05 DB-Script users         | Mini-Task, kommt in Sprint 2 als erstes — Auth-Tests laufen mit Fixture-Daten |
| T-07 RBAC-Middleware         | Braucht T-06; Sprint 2                                                        |
| T-08 React Login-UI          | Sinnvoll erst nach T-07; Sprint 2                                             |
| T-10–T-16 (US-04 Upload)     | Braucht Auth; Sprint 2–3                                                      |
| T-17–T-22 (US-01 Retrieval)  | Braucht Korpus; frühestens Sprint 3–4                                         |
| US-02, US-03, SHOULD-Stories | Sequenziell danach                                                            |

---

## Hinweis zur Velocity

Nach Sprint 1 ist die tatsächliche Geschwindigkeit bekannt und der Umfang von Sprint 2 kann darauf kalibriert werden.

---

*Quellen: Reto/Modul4Tag1/Modul4Tag1_Lab_L1_Output.md · Docs/02_Requirements.md · Docs/07_Definition-of-Done.md*
*Stand: 2026-06-10*
