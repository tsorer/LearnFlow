# LearnFlow — Abschlusspräsentation CAS ADAI

30 Min · 4 Personen (Frank, Niklaus, Reto, Christoph) · Zielpublikum: Dozierende/Peers CAS ADAI

---

## Kritische Anmerkungen zur Struktur (vor der Gliederung)

- **4 Blöcke passen**, aber ohne Zeitbudget pro Block läuft man in genau das Muster,
  das unter Punkt 4 als Learning beschrieben wird: man dreht sich im Kreis. Vorschlag
  unten mit harten Zeitboxen + 1 Timekeeper.
- **Demo zuerst ist die richtige Wahl** (Aufmerksamkeit hoch, Publikum sieht sofort
  den Nutzen statt erst Architektur zu hören) — aber genau deshalb ist sie auch das
  grösste Risiko fürs restliche Timing und den ersten Eindruck. Braucht zwingend
  einen Fallback (Screenshots/kurze Aufzeichnung), falls Stack/Netz nicht mitspielt.
  Die Pitch-Folien (Modul3Tag2) hatten dafür bereits Backup-Folien vorgesehen — gleiches
  Prinzip hier übernehmen.
- **Technischer Aufbau**: Nicht die ADR-Detailfolie (6 von 8) aus dem Architektur-Pitch
  1:1 wiederverwenden — die war für ein anderes Publikum (Architektur-Review Modul 3)
  gedacht und ist inzwischen Ist-Zustand, nicht mehr Entscheid. Nur die zwei Diagramme,
  die man für die Demo tatsächlich braucht (Container + RAG-Flow/Fail-closed), plus
  **einen** neuen Punkt: die Eval-Pipeline (ADR-009, CI-Gate) — die macht die
  „Halluzinationsrate ≈ 0 %"-Behauptung aus der Demo erst überprüfbar statt nur behauptet.
- **Projekt/Team**: „Setting" (Git, Claude Code, Reviews via Claude, KI-unterstützte
  Issues) ist stark, aber nur als Behauptung schwach — **ein** konkretes Beispiel
  (Screenshot eines PR-Reviews oder eines von Claude mitformulierten Issues) trägt
  mehr als drei Sätze Beschreibung.
- **Herausforderungen/Learnings**: „KI findet immer etwas, das kann endlos sein" ist
  ein gutes Learning, aber nur mit einem echten Beispiel glaubwürdig. Lieber 2–3
  Beispiele mit Tiefe als eine Liste allgemeiner Beobachtungen.
- **Nicht ergänzen:** Roadmap/Post-MVP im Detail, zweite Live-Demo-Runde, vollständige
  ADR-Liste, Team-Retro im Stil einer Sprint-Retrospektive. Alles davon bläht auf, ohne
  fürs Publikum neue Information zu liefern.

---

## Zeitbudget (30 Min total, harte Boxen)

| # | Block | Dauer | Wer |
|---|---|---|---|
| 0 | Einstieg: Problem in 1 Satz | 1–2 Min | 1 Person |
| 1 | Live-Demo | 8–9 Min | 1–2 Personen |
| 2 | Technischer Aufbau | 6–7 Min | 1 Person |
| 3 | Projekt & Team | 5–6 Min | 1 Person |
| 4 | Herausforderungen & Learnings | 5 Min | 1–2 Personen |
| 5 | Fazit & Ausblick | 1–2 Min | 1 Person |

→ jede Person hat einen klaren Hauptblock; Rollen oben sind Vorschlag, nicht Zuteilung.

---

## 0 · Einstieg (kurz halten) (Christoph)

- Ein Satz: *„LearnFlow macht internes Wissen für neue Mitarbeitende sofort zugänglich
  — quellenbelegte KI-Antworten aus einem kuratierten Korpus, mit der Garantie: keine
  Antwort ohne Beleg."*

---

## 1 · Live-Demo (Kern der Präsentation) (Reto)

**Leitidee:** nicht Feature-Liste abklappern, sondern **eine Story entlang einer
Persona** (Laras erster Tag) — das erzählt sich von selbst und vermeidet Redundanz.

- **Stefan:** Dokument hochladen → Worker verarbeitet (Fortschrittsanzeige)
  → Dokument ist Quelle
- **Quiz:** Stefan gibt eine KI-generierte Frage frei → Lara absolviert Quiz, sieht
  Erklärung + Quelllink
- **Lara fragt etwas Reguläres** → quellenbelegte Antwort, Klick auf Quelle öffnet
  Originaldokument mit Hervorhebung (US-01)
- **Lara fragt etwas ausserhalb des Korpus** → System sagt „weiss ich nicht" statt zu
  halluzinieren — *das* ist das Produktversprechen, hier laut aussprechen
- **Konfidenz-Badge** an einer Grenzfall-Antwort zeigen (Hoch / Eingeschränkt belegt) —
  macht die Fail-closed-Pipeline aus Block 2 sichtbar, bevor sie erklärt wird
- **Feedback geben** (👍/👎 + Kategorie) — kurz, 1 Klick reicht

- **Admin-Panel (falls Zeit reicht):** Schwellenwert live ändern, Wirkung sofort ohne
  Deployment — sonst weglassen, ist Bonus, kein Muss

**Fallback:** kurze Aufzeichnung/Screenshots bereithalten, falls Demo-Umgebung nicht
mitspielt — nicht live improvisieren müssen.

- todo: Logins nach Personas (Stefan, Laura, Admin)
- Frage ohne Dokument, Dokumentupload, gleiche Frage wird beantwortet
- Quiz evtl. streichen


---

## 2 · Technischer Aufbau (Niklaus, Reto)

**Leitidee:** nur zeigen, was die Demo erklärt — nicht die volle Architektur-Story
nochmal aufrollen.

- **Container-Diagramm** (C4-C2): Web App / API / Worker / DB, Docker Compose,
  4 Container — 1 Minute, dient nur als Landkarte für das Folgende
- **RAG-Request-Flow:** Query → Embedding → Hybrid-Retrieval (Dense + Sparse, RRF) →
  Konfidenz-Pipeline → Antwort
- **Fail-closed-Konfidenz-Pipeline (ADR-008):** 3 Stufen, jede Stufe kann unterdrücken
  — genau das, was in der Demo als „weiss ich nicht" sichtbar war
- **Neu gegenüber dem Architektur-Pitch — Eval als Beleg statt Behauptung (ADR-009):**
  Gold-Eval-Dataset, RAGAS-Metriken, Out-of-Corpus-Test als CI-Gate (T-28, T-56) —
  macht „Halluzinationsrate ≈ 0 %" messbar statt nur postuliert


- bezug auf das was in teil1 gezeigt wurde
---

## 3 · Projekt & Team (Frank)

- **Vorgehen:** User Stories/MoSCoW → ADRs (`Docs/` als Single Source of Truth) → C4 →
  Issues sprintweise abgearbeitet (T-01 … T-64) — kurz den Bezug zu den Unterrichts-
  modulen herstellen (Requirements Engineering, ADRs/C4, RAG-Grundlagen, Eval/RAGAS,
  Security & Ethik Modul 8 — z. B. Datenminimierung/Pseudonymisierung/IP-freies
  Zugriffslog als konkret umgesetztes Beispiel)
- **Setting:**
  - GitHub-Repo, Feature-Branches + PR-Pflicht, CI (backend/frontend/e2e als Required
    Checks)
  - Claude Code als Entwicklungswerkzeug — `CLAUDE.md` als verbindliches Regelwerk
    (Spec-first, Definition of Done, Tripwires)
  - PR-Reviews automatisiert über Claude-GitHub-Action
  - Issues teilweise KI-mitformuliert/-geplant (Backlog-Pflege mit Claude)
  - **Ein konkretes Beispiel zeigen** (Screenshot PR-Review-Kommentar oder Issue-Text)
    statt nur zu behaupten „wir haben mit KI gearbeitet"


- single source of truth
- abweichungen von theorie (z.b. Claude-Reviews)

---

## 4 · Herausforderungen & Learnings — Bezug zum Unterricht (Christoph)

**Leitidee:** 2–3 Learnings, je mit einem echten Beispiel aus dem Projekt — keine
allgemeine Liste von Beobachtungen.

- **KI bläht alles auf**
  - KI kann Ideen liefern und diese auch kritisch hinterfragen — das kann jedoch in
    einem endlosen Prozess enden (Beispiel: beim Definieren der Use Cases machten wir
    diese Erfahrung)
  - Eine kritisch eingestellte KI findet immer etwas — das kann endlos weitergehen
    (viele Review-Loops)
- **Empfohlene Lösung nicht immer die bessere** — Beispiel T-28: naheliegend gewesen
  wäre, schwache Kontext-Chunks unter der Similarity-Schwelle herauszufiltern; das
  hätte das Retrieval aber schleichend Richtung Dense-only verschoben und genau die
  Sparse-Stärke ausgehebelt, die für deutsche Komposita/Akronyme eingeführt wurde.
  Erst der Test am Gold-Dataset zeigte, dass die ungefilterte Variante fail-closed
  ehrlicher ist.
- **Evtl. weitere Beispiele (optional, falls Zeit reicht):**
  - Fail-closed nur behauptet, nicht getestet — Code nannte sich im Docstring
    „fail-closed", verhielt sich bei kaputten Config-Werten aber fail-offen
    → **Learning:** von KI generierter Code kann die eigene Dokumentation falsch
    beschreiben; nur gezielte Tests/Review gegen die Architekturentscheide (nicht
    gegen die Selbstbeschreibung des Codes) decken das auf
  - Schwellenwerte kalibrieren statt raten — Übergang von geschätzten/empirisch
    getunten Werten zu einem systematischen Kalibrierungs-Loop (Snapshot +
    Offline-Replay, T-57)


- schlägt lösungen vor für probleme die man noch gar nicht kannte
---

## 5 · Fazit & Ausblick (Niklas)
- Lokale Modelle (Möglichkeiten)

- Bewusst offen/zurückgestellt: Config-Konsolidierung (T-63/T-64), Kalibrierungs-Loop
  (T-57) — nicht als Rückstand entschuldigen, sondern als bewusste Priorisierung
  framen
- Ein Satz Ausblick Post-MVP (SSO, Stale-Content-Erkennung) — keine Detailroadmap

**Nicht erwähnen:** zeitliche Angaben, Deadlines etc. Höchstens Sprints, aber keine
Deadlines und geplanten Stunden o. Ä.
