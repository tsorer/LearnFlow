# Ü1 Teil 2 · Advocatus Diaboli — Modularer Monolith

*LearnFlow · Modul 3 Tag 2 · Reto Stucki · 2026-06-03*
*Quellen: Docs/04_ADR-001_Architekturstil.md · Docs/03_QualityAttributes.md · Docs/06_Architecture-Draft.md*

---

## 1. Warum ist diese Entscheidung für uns FALSCH?

ADR-001 setzt voraus, dass Modul-Grenzen von Anfang an stimmen — und genau das ist bei LearnFlow nicht gesichert. Die Konfidenz-Pipeline (ADR-008) ist konzeptionell noch offen, das Eval-Framework (ADR-009) steht als Spike aus, und das Streaming-vs.-Grounding-Dilemma ist explizit als «offene Frage für Tag 2» markiert (Architecture-Draft). Wir ziehen Grenzen, bevor wir wissen wo sie hingehören.

**Konkreter Widerspruch im Draft:** Der Background Worker (pgqueuer, ADR-006) und der API Server teilen PostgreSQL als einzigen Kommunikationskanal (`pg_notify`). Das ist keine Modul-Grenze — das ist geteilter State über `pg_notify`. Im Monolith fehlt der Zwang, diese Kopplung explizit zu machen.

---

## 2. Was werden wir in 6 Monaten bereuen?

- **Konfidenz-Scoring mitten im API-Server:** ADR-008 beschreibt einen mehrschichtigen Unterdrückungsmechanismus (Quellenprüfung → Score → Self-Check). Im Monolith wird diese Logik unweigerlich direkt in Request-Handler einwachsen — nicht in ein isoliertes Modul. Austausch ohne Seiteneffekte (Maintainability-NFA) wird zur Illusion.
- **PostgreSQL als Single Point of Failure:** Architecture-Draft nennt es explizit — «kein Replica, kein Backup definiert». Im Monolith skalieren wir alle Module zusammen oder gar nicht. Wenn die DB weg ist, ist alles weg.
- **Testbarkeit der RAG-Pipeline:** Reliability-NFA fordert, jede Komponente einzeln isolierbar zu testen. Ohne durchgesetzte Modul-Interfaces (ADR-001 sagt «Code-Review checkt» — kein CI-Gate) werden Unit-Tests faktisch Integrationstests mit DB-Dependency.

---

## 3. Welches Pattern wäre ehrlich gesagt besser?

**Klassischer geschichteter Monolith** (API → Service → Repository → DB) statt «Modularer Monolith».

ADR-001 selbst benennt das Risiko: *«ohne explizit durchgesetzte Modul-Grenzen entsteht über Zeit ein Big-Ball-of-Mud-Monolith»* — und setzt als Mitigation nur Code-Review an, kein technisches Gate. Mit 360 h und KI-generiertem Code (Claude Code) ist manuelles Code-Review der schwächste mögliche Schutzmechanismus.

---

## 4. Was müssen wir tun damit unsere Wahl wirklich funktioniert?

| Massnahme                                                         | Warum zwingend                                                                              |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| **Modul-Grenzen als `import-linter`-Regel in CI**                 | Code-Review allein reicht bei KI-generiertem Code nicht — ADR-001 benennt das Risiko selbst |
| **Konfidenz-Scoring als eigenes Modul von Tag 1** (auch als Stub) | ADR-008 offen + Maintainability-NFA: austauschbar ohne Seiteneffekte                        |
| **PostgreSQL Backup + Read-Replica vor Pilot-Start**              | Architecture-Draft: explizit als ungelöstes Risiko markiert                                 |
| **Streaming-vs.-Grounding-Konflikt auflösen**                     | Offene Architektur-Frage (Draft) — blockiert Reliability-NFA (Halluzinationsrate = 0 %)     |

---

## Fazit

**Wir bleiben bei ADR-001 — aber «Proposed» muss «Accepted mit Bedingungen» werden.**

Die vier Massnahmen oben sind keine Optionen, sondern Voraussetzungen. Insbesondere der CI-Gate für Modul-Grenzen: Ohne ihn ist «Modularer Monolith» nur ein Name.

## Team-Diskussion

- Wir bleiben bim Modularen Monolithen

- Wir grenzen die Module sauber ab, damit man sie später in einzelne Container auslagern kann
