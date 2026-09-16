# Block 3 — „Wie haben wir es umgesetzt" (Frank, ~7 Min)

**Ideensammlung**, kein fertiges Skript. Zweck: Material sammeln, dann auf 7 Minuten
schneiden. Alles unten ist mit Quellen im Repo belegt — Zahlen aus GitHub (Stand
2026-09-20), Beispiele aus `Frank/Prompts/` (40 exportierte Chatverläufe).

Bezug: `Artefakten/Abschlusspräsentation/Inhalte_Abschlusspräsentation.md` (Block 3
„Projekt & Team"). Vorgabe von dort: **keine Zeitangaben, keine Deadlines, keine
Stundenbudgets** — Sprints als Struktur nennen ist erlaubt.

---

## 0 · Die Kernbotschaft (ein Satz, an dem alles hängt)

> **„Wir haben nicht Code geschrieben, sondern ein Regelwerk gebaut, das Code erzeugt
> — und die Qualitätssicherung dorthin verschoben, wo die Fehler entstehen."**

Alternative Formulierung, falls die erste zu steil klingt:

> „Unser Entwicklungsprozess ist darauf ausgelegt, dass die KI den Code schreibt und
> wir entscheiden. Damit das funktioniert, mussten Entscheide schriftlich, auffindbar
> und maschinell prüfbar sein."

Das ist in `Docs/07_Definition-of-Done.md` wörtlich als Leitprinzip verankert:
*„Code wird KI-gestützt mit Claude Code erzeugt; die Teammitglieder sind primär
Reviewer und Verifizierer. Daraus folgt: das menschliche Review und die automatisierten
Gates sind die Qualitätssicherung, nicht das Schreiben des Codes."*

→ Diesen Satz **zitieren**. Er ist der rote Faden für alle fünf Unterthemen.

---

## 1 · Zeitbudget-Vorschlag (7 Min, hart)

| # | Thema | Zeit | Kern |
|---|---|---|---|
| 3.0 | Einstieg: Leitprinzip | 0:30 | DoD-Zitat, der rote Faden |
| 3.1 | Vom Entscheid zum ADR | 1:00 | `Docs/` als Single Source of Truth |
| 3.2 | Vom ADR zum Issue | 1:00 | Backlog-Genese, 39 geplant / 30 gewachsen |
| 3.3 | Sprints | 0:45 | 9 Meilensteine, Rhythmus statt Scrum-Zeremonie |
| 3.4 | Umsetzungsprozess | 1:45 | Der Loop: Plan → Rückfragen → Spec → Code → Verifikation |
| 3.5 | Review-Prozess | 1:30 | Mehrschichtig: KI ↔ KI ↔ Mensch, Mensch entscheidet |
| 3.6 | Übergabe / Pointe | 0:30 | Was der Prozess gekostet und gebracht hat |

> Realistisch: Man schafft **ein** vertieftes Beispiel, nicht fünf. Schnittplan in
> Abschnitt 8.

---

## 2 · ADRs — Entscheide, die nicht verhandelbar sind

### Was erzählen

- **10 ADRs** (`Docs/04_ADR-001` … `ADR-010`), entstanden vor der ersten Zeile
  Produktionscode. Nicht als Pflichtübung aus dem Unterricht, sondern weil sie die
  einzige Möglichkeit waren, der KI eine verbindliche Vorgabe zu geben.
- **ADRs sind lebende Dokumente, nicht Archiv.** ADR-008 (Fail-closed-Konfidenz-Pipeline)
  trägt im Kopf sechs Aktualisierungsdaten — jede davon ist eine Erkenntnis aus einem
  konkreten Ticket, die zurück in den Entscheid geflossen ist.
- Status ehrlich lassen: einige ADRs stehen bis heute auf `Proposed`
  (ADR-003/004/005/007/009) — bewusst, nicht aus Nachlässigkeit.

### Der Mechanismus, der ADRs wirksam macht

`CLAUDE.md` übersetzt die ADRs in **Tripwires** — Regeln, die die KI nicht überschreiten
darf. Wörtlich aus der Datei:

> „**Fail-closed-Schwellen (ADR-008) nicht aufweichen** (z. B. `>=` → `>`);
> Eval-Gates (ADR-009) nicht umgehen."

Das ist der Unterschied zwischen einem Dokument, das existiert, und einem Entscheid,
der **wirkt**. Beleg, dass es greift — aus `Frank/Prompts/2026-08-09_T-24-Konfidenz-Schwellenwert.md`:

> „Die Band-Semantik steht in den `description`-Spalten: `score >= high` → Hoch,
> `score >= medium` → Mittel, darunter unterdrückt — **die `>=` bleiben `>=`
> (CLAUDE.md-Tripwire zu ADR-008)**."

Die KI begründet ihre eigene Zeile mit der Regel aus `CLAUDE.md`. Genau dafür ist die
Datei da.

### Mögliche Folie

- Links: ADR-008-Kopfzeile mit den sechs Aktualisierungsdaten (Screenshot).
- Rechts: die Tripwire-Zeile aus `CLAUDE.md`.
- Pfeil dazwischen: „Entscheid → Regel → prüfbar".

---

## 3 · Issues — wie der Backlog entstanden ist (und weiter wuchs)

### Die Zahlen (belastbar, aus GitHub)

| Kennzahl | Wert |
|---|---|
| Issues gesamt | **69** (61 geschlossen, 8 offen) |
| davon an **einem Tag** angelegt | **39** — die Erst-Planung `T-01 … T-38` |
| davon **später** entstanden | **30** — `T-39 … T-65` plus ungenummerte Bugs |
| Pull Requests | **74** (69 gemergt) |
| Sprint-Meilensteine | **9** (Sprint 0 … Sprint 8) |

### Die Geschichte dahinter — zwei Quellen für Issues

**(a) Geplant: User Stories → MoSCoW → Issues.** Der Erst-Backlog `T-01 … T-38` wurde
aus `Docs/01_UserStories.md` / `02_Requirements.md` abgeleitet und per Skript in einem
Rutsch angelegt (`Reto/Modul4Tag1/create-issues.ps1`) — inklusive Milestone,
Project-Board-Eintrag und der **Definition of Done als Checkliste in jedem Issue-Body**.
Das Template dazu: `.github/ISSUE_TEMPLATE/task.md`.

→ Pointe: Die DoD steht nicht in einem Wiki, das niemand liest. Sie steht **in jedem
einzelnen Ticket** als abhakbare Liste.

**(b) Gewachsen: Reviews und Evals gebären Issues.** 30 von 69 Issues gab es am Anfang
nicht. Sie entstanden dort, wo sie auffielen. Das ist die eigentlich interessante
Hälfte.

### Konkretes Beispiel — T-46 (Issue #90), ein Issue aus einem Review

Kette, vollständig im Repo nachvollziehbar:

1. Review zu PR #86 (T-19) → Frage: Soll `StageInfo.id` ein Enum sein?
2. Entscheid: **nein** — weil `DebugInfo` laut Spec „nicht Teil des fachlichen
   Vertrags" ist.
3. Nachfrage des Nutzers (wörtlich aus dem Verlauf):
   > „OK, setze die beiden Punkte um und **erstelle ein neues Issue**, dass geprüft
   > werden soll, ob DebugInfo (und eventuell auch andere Variablen?) als Enum definiert
   > werden sollte und das es **in einem ADR dokumentiert** werden sollte."
4. Daraus Issue #90. Im Issue-Text steht die Begründung, warum es das Issue braucht:
   > „Der Entscheid steht **nur** als Schema-Beschreibung in `openapi.yaml`, nicht in
   > einem ADR. Der Entscheid ist damit schlecht auffindbar und wird bei jeder
   > Berührung neu aufgemacht."

→ **Das ist der Satz für die Folie.** Ein Entscheid, der nicht am richtigen Ort steht,
wird in jeder Session neu diskutiert. Deshalb der Reflex: Entscheid → ADR, offene Frage
→ Issue.

### Zweites Beispiel — Issue statt Kommentar, die Triage-Frage

Nicht jeder Fund wird ein Ticket. Der Nutzer wägt ab (wörtlich):

> „Könnte Punkt 1 zusammen mit T-28 umgesetzt werden? Dann wäre ich eher für einen
> Kommentar dort als ein eigenes Issue."

und an anderer Stelle:

> „Ist Punkt 2 nicht das, was wir letzte Woche bereits als Kommentar bei T-37 erfasst
> haben? Oder sollte es besser ein Kommentar bei T-38 sein? Wobei die beiden Tickets eh
> zusammen umgesetzt werden."

→ Pointe: Die KI schlägt für jeden Fund ein Issue vor. **Das Backlog sauber zu halten,
ist Menschenarbeit** — sie braucht das Gedächtnis über Wochen, das die KI pro Session
nicht hat. (Vorsicht: grenzt an Christophs Block 4 „KI bläht alles auf" — hier nur als
Prozessschritt nennen, nicht als Learning ausbauen.)

---

## 4 · Sprints — Rhythmus, nicht Zeremonie

### Was erzählen

- **9 Meilensteine** in GitHub: Sprint 0 (Infrastruktur) → Sprint 8.
- Kein Scrum-Theater: keine Dailys, keine Velocity-Rituale, keine Retro-Formate.
  Was übernommen wurde, ist das, was bei einem nebenberuflichen Team trägt:
  **feste Zeitbox, Milestone am Issue, Board, klare Reihenfolge.**
- Story Points wurden im Project Board gepflegt (1/2/3/5/8), aber nicht zur
  Fortschrittsmessung hochgerechnet.

### Der inhaltliche Bogen (gut als eine Folie, eine Zeile pro Sprint)

| Sprint | Thema | Beispiel-Tickets |
|---|---|---|
| 0–1 | Infrastruktur & technische Grundlagen | DB-Schema, OpenAPI-Grundgerüst, Login, pgqueuer |
| 2–3 | Skelett steht: Upload, RBAC, Worker | Parsing/Chunking, Embedding + pgvector, Branch Protection |
| 4 | Die Pipeline entsteht | `POST /query` (Retrieval), LLM-Generierung, Feedback-Tabelle |
| 5 | Fail-closed wird echt | Quellenreferenz-Validierung, Konfidenz-Score, Self-Check, Unterdrückungslogik |
| 6 | Qualität messbar machen | Gold-Eval-Dataset, PDF-Textextraktion, Quiz, Konfidenz-Badges |
| 7 | Sichtbarkeit & Betrieb | Admin-Seite, Dashboards, Dokumentviewer, Performance-Test |
| 8 | Messen statt raten | In-Corpus-Eval, Kalibrierungs-Loop, e2e-Isolation, Pipeline-Optimierung |

→ **Die Pointe der Tabelle:** Der Verlauf ist kein Zufall. Sprint 1–4 bauen, Sprint 5
härtet ab, ab Sprint 6 wird gemessen. Die Reihenfolge folgt der Risiko-Priorität aus den
Quality Attributes — Reliability vor Feature-Breite.

→ Falls Zeit fehlt: nur die drei Phasenwörter zeigen — **Bauen → Absichern → Messen.**

---

## 5 · Der Umsetzungsprozess — der Loop, den wir jedes Mal gelaufen sind

`CLAUDE.md` hat einen Abschnitt „Entwicklungsprozess (verbindlich für jeden Issue)".
Der ist nicht Theorie — er lässt sich in den 40 Chatverläufen Schritt für Schritt
nachweisen. 18 der Verläufe beginnen wörtlich mit einem Planungsauftrag.

### Der Ablauf als Folie (6 Schritte)

```
1  Issue lesen          gh issue view — AK und Scope erfassen
2  Spec prüfen          Docs/ gegenlesen; Widerspruch → zuerst rückfragen
3  Plan + Rückfragen    Plan-Modus, kein Code. Offene Punkte werden entschieden,
                        nicht geraten
4  Spec zuerst          openapi.yaml vor dem Code (ADR-010), Typen generieren
5  Code + Tests         kleinste Änderung, die das Problem löst
6  Verifikation         make qa + Akzeptanzkriterien manuell am laufenden Stack
```

### Der Standard-Einstieg (wörtlich, so oder ähnlich 18×)

> „Erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/106"

und in der Variante, die den Prozess am besten beschreibt:

> „als nächstes steht die Umsetzung von […] an. Erstelle in git einen neuen Branch und
> erstelle einen Plan, wie das Issue umgesetzt werden kann. **Stelle mir vor der
> Umsetzung Fragen, bis alle Unklarheiten geklärt sind.**"

→ **Das ist der wichtigste Satz des ganzen Blocks.** Nicht „schreib mir Code", sondern
„frag mich, bis du es verstanden hast". Der Plan ist das eigentliche Arbeitsprodukt;
der Code fällt danach fast beiläufig an.

### Beispiel A — T-24: Der Plan deckt einen Doku-Widerspruch auf

Aus `Frank/Prompts/2026-08-09_T-24-Konfidenz-Schwellenwert.md`. Statt sofort zu
implementieren, lieferte der Plan eine Bestandsaufnahme — und einen Fund, den niemand
gesucht hatte:

> „**Widerspruch in den Docs:** `Ops/07_Pilotstart-Checkliste.md` legt
> `confidence_threshold_high` / `_medium` / `stale_threshold_days` von Hand per `INSERT`
> an; das ERD kennt diese Keys nicht und nennt für Stale den real existierenden Key
> `stale_days`."

Ergebnis: eine Rückfrage-Runde mit drei Entscheiden (welche Keys, wie weit geht das
Backend, Cache oder nicht) — **getroffen vom Menschen, dokumentiert als Tabelle, dann
erst Code.**

Zusatz aus demselben Verlauf, schöner Realitätsbeweis: Vor dem ersten Schritt prüfte die
KI den Git-Stand erneut und stellte fest, dass die Migration `0007` noch gar nicht auf
`main` lag, sondern in einem offenen PR. Ein Branch von `main` wäre nicht lauffähig
gewesen. Entscheid: den Branch ausnahmsweise stapeln.

→ Pointe: **Planen heisst hier: den Ist-Zustand messen, nicht den Soll-Zustand annehmen.**

### Beispiel B — T-51: Annahmen messen statt schätzen

Aus `Frank/Prompts/2026-09-11_T-51-T-61-Fortschritts-Zeitstempel-PR-134.md`, „Schritt 0"
des Plans. Für einen Timeout-Wert wurde nicht geschätzt, sondern am laufenden Stack
gemessen:

| Grösse | Wert |
|---|---|
| Parsing (~576 Seiten / 2100 Chunks) | 29,33 s |
| Chunking | 2,85 s |
| Speichern (1850 Chunks, echte DB) | 4,39 s |
| Embedding-Batch-Retry (harter Boden) | ~120 s |
| **stall = max(…) × 2** | **240 s → aufgerundet 300 s** |

Der Wert `300` steht heute in der Migration `0020` — und die Herleitung als Nachtrag
„Woher die 300 s kommen" in **ADR-006**. Der Kreis schliesst sich: Umsetzung erzeugt
Wissen, Wissen geht zurück in den Entscheid.

→ Wenn nur **ein** Beispiel Platz hat: dieses. Es zeigt Plan, Messung, Entscheid,
Dokumentation und den Rückfluss ins ADR in einer einzigen Folie.

### Nebenbei erwähnenswert (je ein Halbsatz)

- **Spec zuerst** (ADR-010): Ein neuer Endpoint braucht im selben PR drei Dinge —
  `openapi.yaml`, Route im Backend, generierte Frontend-Typen. Ein Test
  (`tests/test_rbac.py`) prüft **beide Richtungen** Code ↔ Spec. Drift ist damit nicht
  Disziplinfrage, sondern rote CI.
- **Der Mensch entscheidet Scope** — wörtlich:
  > „Entscheid: eigenen Endpoint erstellen. Hier und nicht in einem eigenen Issue.
  > Analog `sample_chunks`"
- **Der Mensch ist das Langzeitgedächtnis** — wörtlich, zum Rate-Limit-Schlüssel:
  > „Es muss pro IP-Adresse sein, da man sonst zu einfach Benutzer aussperren kann.
  > (Haben wir schon mal ausdiskutiert)."

---

## 6 · Der Review-Prozess — die interessanteste Abweichung von der Lehre

### Die Ausgangslage ehrlich benennen

Wenn die KI den Code schreibt, ist der klassische Vier-Augen-Review über den Code
**nicht mehr die stärkste Kontrolle** — der Mensch hat den Code nicht geschrieben und
kann ihn nicht Zeile für Zeile im Kopf haben. Unsere Antwort: Review in **mehreren
Schichten**, von denen keine allein trägt.

### Die vier Schichten (Folie)

| Schicht | Was | Wer |
|---|---|---|
| 1 | **Automatische Gates** — `backend` / `frontend` / `e2e` als Required Checks, Branch Protection auf `main` | CI |
| 2 | **KI-Review gegen den PR** — `/code-review <PR-URL>`, Befunde mit Datei:Zeile | Claude |
| 3 | **Gegen-Review** — eine *zweite, unabhängige* KI-Session bewertet die Befunde der ersten | Claude |
| 4 | **Entscheid & Approve** — Triage, Priorisierung, Approve durch eine zweite Person | Mensch |

Belege im Repo: **16 der 40 exportierten Verläufe sind reine Review-Protokolle**, und
**24-mal** beginnt ein Prompt mit „bewerte…" — also mit Schicht 3.

### Die Konventionen, die den Review lesbar halten (wörtlich vom Nutzer)

> „Vor dem Erstellen des PR ein Squash machen, damit der Review **nur ein Commit**
> sieht. Wenn es Korrekturen gibt, diese **immer einzeln** pushen, damit die Korrekturen
> nachvollziehbar sind."

→ Kleine Regel, grosse Wirkung: Der Reviewer sieht erst einen sauberen Gesamtdiff, dann
je Korrektur einen eigenen Commit. Nicht 14 „wip"-Commits.

### Beispiel C — PR #91 (T-45): Was ein Review leistet, das kein Mensch leisten würde

Aus `Frank/Prompts/2026-08-24_PR-91-Review-T-45.md`. PR einer **anderen Person** im
Team, reviewt von Frank mit Claude. Verdikt: *„approvebar nach drei kleinen Korrekturen,
keine Blocker."* Drei Dinge daran sind vorzeigbar:

1. **Ein Befund, den man nur durch Messen findet:**
   > „das e2e-Login-Budget ist nach dem PR bei 4 von 5, und T-15 bringt den fünften."

   Die Login-Requests pro Testlauf wurden *gezählt* und gegen das Rate-Limit `5/minute`
   gestellt. Ein noch nicht gemergter Branch hätte die Suite über die Kante gekippt.
   (Daraus wurde später Issue #131, T-60.)

2. **Zwei Verdachtsmomente, die sich beim Nachprüfen auflösten** — und deshalb *nicht*
   in den Kommentar kamen. Das Protokoll hält beide fest. Ein Review, das auch
   dokumentiert, was **kein** Problem ist, spart dem Autor die Verteidigung.

3. **Eine Rückfrage statt eines Befunds** — die KI fand eine Notiz, wonach das Team den
   Rate-Limit-Schlüssel schon einmal entschieden hatte, und der PR drehte diesen
   Entscheid um, ohne es zu erwähnen. Sie hat es nicht als Fehler gemeldet, sondern
   gefragt. Die Auflösung kam vom Menschen:
   > „Zu der Notiz: Ich hatte damals das Login im Hinterkopf und nicht auf alles.
   > So passt es für mich."

→ **Genau hier liegt die Arbeitsteilung.** Die KI findet die Inkonsistenz. Nur der
Mensch weiss, welche der beiden Versionen die gemeinte war.

### Beispiel D — Der Mensch triagiert, die KI liefert die Entscheidungsgrundlage

Aus `Frank/Prompts/2026-08-12_PR-76-Review-T-39.md` (Review zu PR #76, fünf Befunde).
Die entscheidende Frage des Nutzers war nicht „stimmt das?", sondern:

> „**Wie schwerwiegend sind die Befunde? Was passiert, wenn es nicht angepasst wird?**"

Die Antwort war eine Tabelle: *Wirkt heute? · Scharf ab welchem Ticket? · Folge, wenn
nichts passiert* — und die Einordnung „keiner der fünf Befunde macht heute etwas kaputt,
alle sind latent". Ergebnis: drei Einzeiler sofort im PR, einer als Folge-Ticket, einer
als bewusstes Restrisiko.

→ Pointe für die Folie: **Nicht jeder Befund ist ein Auftrag.** Die Frage „was passiert,
wenn wir nichts tun" ist das, was aus einer Befundliste eine Entscheidung macht — und
sie stellt der Mensch.

### Typische Nutzer-Antworten im Review (als „O-Ton-Wolke" auf einer Folie)

> „Ja, fix alle bis auf #9 und #11" ·
> „Punkt 1: Kommentieren. Den Rest wie vorgeschlagen umsetzen." ·
> „bitte auf deutsch. Punkt 1 ist nicht relevant, da es noch nie produktiv im Einsatz war." ·
> „bewerte kritisch diese 3 Befunde:" ·
> „der andere Review-Prozess hat folgendes gefunden:" ·
> „die Korrekturen wurden umgesetzt, PR kann nun approved werden, oder?"

→ Eine Folie nur mit diesen Zeilen erzählt den ganzen Review-Prozess ohne ein einziges
Diagramm. **Starker Kandidat für die Schlussfolie des Blocks.**

---

## 7 · Zahlen auf einen Blick (eine Folie, falls gewünscht)

| | |
|---|---|
| ADRs | **10** · ADR-008 sechsmal nachgeführt |
| Issues | **69** — 39 geplant, **30 im Lauf entstanden** |
| Pull Requests | **74**, davon **69 gemergt** |
| Sprints | **9** (Sprint 0 – 8) |
| Required Checks pro PR | **3** — `backend`, `frontend`, `e2e` |
| DoD-Kriterien pro Issue | **7**, als Checkliste im Issue-Body |
| Dokumentierte Chatverläufe | **40** (`Frank/Prompts/`), davon **16** Review-Protokolle |

> Vorsicht Dosierung: Zahlen wirken nur, wenn sie **eine** Aussage stützen. Kandidat:
> „39 geplant, 30 entstanden" — das belegt, dass der Prozess lernfähig war, ohne dass
> man es behaupten muss.

---

## 8 · Wenn die Zeit knapp wird (Schnittplan)

**Muss drin bleiben:**
- Das DoD-Leitprinzip (Abschnitt 0) — ohne das ergibt der Rest keinen Sinn.
- Der Loop (Abschnitt 5, die 6 Schritte).
- Die vier Review-Schichten (Abschnitt 6) + **ein** Beispiel.
- „39 geplant / 30 entstanden".

**Zuerst streichen:**
- Die Sprint-Tabelle im Detail → auf „Bauen → Absichern → Messen" eindampfen.
- Beispiel A (T-24) — Beispiel B (T-51) ist stärker und deckt dasselbe ab.
- Die vollständige Zahlen-Folie.

**Empfohlene Beispiel-Auswahl bei 7 Minuten: B (T-51 Messung) + C oder D (Review).**
Eines für „so haben wir gebaut", eines für „so haben wir geprüft".

---

## 9 · Abgrenzung — was in diesen Block *nicht* gehört

| Thema | Gehört zu |
|---|---|
| Wie die Antwort technisch entsteht (RAG, Fail-closed, Eval-Metriken) | Block 2 |
| „KI bläht alles auf", endlose Review-Loops, empfohlene Lösung ≠ bessere | Block 4 |
| Fail-closed war nur behauptet, nicht getestet | Block 4 — **nicht vorwegnehmen** |
| Roadmap, Post-MVP, lokale Modelle | Block 5 |
| Zeitangaben, Deadlines, Stundenbudget | überall gestrichen (Teamentscheid) |

**Gefahrenstelle:** Abschnitt 3 („Backlog sauber halten ist Menschenarbeit") und
Abschnitt 6 liegen nah an den Learnings aus Block 4. Lösung: hier nur den
**Prozessschritt** zeigen, die **Bewertung** dem Block-4-Part überlassen. Vorher kurz
absprechen.

---

## 10 · Übergabe zu Block 4 (ein Satz)

> „Das ist der Prozess, wie er auf dem Papier steht und wie er gelaufen ist. Was er uns
> unterwegs gekostet hat und was wir dabei gelernt haben — dazu jetzt Christoph."

---

## 11 · Offene To-dos für diesen Block

- [ ] Screenshots ziehen: ADR-008-Kopf (Aktualisierungsdaten), ein Issue mit
      DoD-Checkliste, ein PR-Review-Kommentar mit Befunden, GitHub-Milestone-Übersicht
- [ ] Entscheiden: Foliensatz in HTML (wie `Niklaus/Abschlusspräsentation/`) oder
      klassisch
- [ ] Abgrenzung zu Block 4 klären (siehe Abschnitt 9)
- [ ] Zahlen kurz vor der Präsentation nachziehen — sie ändern sich noch
- [ ] Einmal auf Zeit sprechen; erfahrungsgemäss sind 7 Minuten weniger, als es aussieht

---

## 12 · Foliensatz und GitHub-Live-Teil

**Folien:** `Frank/AbschlussPraesi/Block3_Umsetzung.html` — 6 Folien, gleiche
Formensprache wie Block 2 und 5 (1600×900, Pfeiltasten/Leertaste, Punkte unten).

| # | Folie | Live in GitHub? |
|---|---|---|
| 1 | Leitprinzip — „Wir haben den Code nicht geschrieben. Wir haben entschieden." | — |
| 2 | ADRs — Entscheid → Regel → geprüfte Codezeile (ADR-008) | — |
| 3 | Issues — „39 geplant. 30 kamen dazu." | **Issue** |
| 4 | Sprints — „Bauen. Absichern. Messen." | **Board** |
| 5 | Umsetzungsprozess — der Loop + Messung statt Schätzung | — |
| 6 | Review — vier Schichten | **Pull Request** |

Die drei Folien tragen ein Abzeichen „↗ live in GitHub". Sie funktionieren **auch ohne
Umschalten** — der Inhalt ist auf der Folie selbst abgebildet (Issue-Karte, Sprint-Liste,
Prüfschichten). Das Abzeichen ist eine Einladung, keine Abhängigkeit.

### Vorzuschlagende Tabs (vorher öffnen, nicht live suchen)

| Folie | Was zeigen | Adresse |
|---|---|---|
| 3 | **Issue #90 (T-46)** — Ticket aus einem Review, mit DoD-Checkliste im Body | `github.com/tsorer/LearnFlow/issues/90` |
| 4 | **Board / Milestones** — Sprint-Meilensteine mit geschlossenen Tickets | `github.com/tsorer/LearnFlow/milestones` · Board: Project 2 |
| 6 | **PR #134 (T-51)** — drei Review-Runden, Korrekturen einzeln nachvollziehbar | `github.com/tsorer/LearnFlow/pull/134` |

> Alternative zu #134, falls ein fremd-reviewter PR besser passt: **PR #91 (T-45)** —
> von einer anderen Person geschrieben, von Frank reviewt, Befund „Login-Budget 4 von 5".
> Das ist die Geschichte auf Folie 6.

### Regie-Hinweise für den Live-Teil

- **Reihenfolge beibehalten:** Folie zeigen → dann umschalten. Nicht umgekehrt; sonst
  erklärt man den Screenshot statt die Aussage.
- **Pro Wechsel maximal 30 Sekunden.** Drei Wechsel à 30 s sind bereits 1:30 von 7:00.
  Wenn die Zeit knapp wird: nur **einen** Live-Teil machen — der PR trägt am meisten,
  weil dort Befunde, Korrekturen und Approve in einer Ansicht sichtbar sind.
- **Zoomstufe im Browser vorher auf ~150 % setzen**, sonst ist im Saal nichts lesbar.
- **Fallback:** Die Folien decken alles ab. Wenn Netz oder Login klemmt — einfach nicht
  umschalten, die Aussage steht.

---

## 13 · Variante B — der chronologische Schnitt

`Frank/AbschlussPraesi/Block3_Umsetzung_VarianteB.html` — 7 Folien, gleiche
Formensprache. Variante A bleibt unverändert als thematischer Schnitt bestehen.

**Leitidee:** derselbe Stoff, aber als Weg erzählt. Zehn Stationen, gruppiert in fünf
Phasen — Anforderungen · Entscheide · Fundament · Takt · Ausbau. Die Phasenleiste oben
zeigt auf jeder Folie, wo man gerade ist.

| # | Folie | Stationen |
|---|---|---|
| 1 | Der Weg — zehn Stationen im Überblick | alle |
| 2 | „Erst die Idee kaputt fragen" | 1 Ideenfindung · 2 User Stories |
| 3 | „Die KI hat unsere eigenen Entscheide auseinandergenommen" | 3 ADRs |
| 4 | „39 Tickets an einem Tag. Neun Sprints." | 4 Issues · 5 Sprints |
| 5 | **„Die Pipeline stand, bevor das erste Feature stand"** | 6 Grundgerüst · 7 CI/Tests |
| 6 | „Plan, Rückfragen, Spec — dann erst Code" | 8 Umsetzung · 9 Review |
| 7 | „30 Tickets, die niemand geplant hatte" | 10 Erweiterung |

### Neue Belege aus `Artefakten/` (vorher nicht verwendet)

**Station 1 — der Kickoff war ein Sparring, kein Brainstorming.**
`Artefakten/Modul1Tag2/LearnFlow_Kickoff_Doku.md`: Phasen 00–04 entlang der
Kickoff-Vorlage, die KI ausdrücklich in der Rolle „skeptischer CTO". Drei
Produktvarianten standen zur Wahl; der Entscheid ist mit vier Gründen protokolliert.
Der beste davon fürs Publikum:

> „Halluzinationen treffen Entwickler:innen, die im Code-Review oder Sparring mit BA
> gegenchecken können — nicht direkt Klient:innen einer Sozialberatung."

→ Das Risiko wurde **bei der Themenwahl** minimiert, nicht erst in der Architektur.

**Station 2 — die Fail-closed-Idee ist älter als die Architektur.**
`Artefakten/Modul2Tag2/requirements_report_learnflow.md` (Requirements-Agent mit
Marktanalyse) empfiehlt als Mitigation gegen „Vertrauensverlust durch eine einzige
falsche Antwort":

> „US-02 technisch so umsetzen, dass Schweigen (keine Antwort) explizit besser ist als
> eine unsichere Antwort — nie ‚raten'."

→ **Aus diesem Satz wurde ADR-008.** Starker Bogen: das Produktversprechen entstand in
der Anforderungsphase, nicht im Code. Derselbe Report stufte US-10/US-11a hoch, fand
US-12 und US-13 neu und splittete US-11 — aus 11 Stories wurden 18 (7 MUST).

**Station 3 — der ADR-Review hat Redis aus dem Projekt geworfen.**
`Artefakten/Modul3Tag1/ADR-Review_Kritik.md` — die KI las die ersten fünf ADRs gegen
und fand einen Widerspruch, den das Team selbst hineingeschrieben hatte:

> „ADR-001 verkauft ‚ein Deployment-Artefakt' als zentralen Vorteil. ADR-002 nennt als
> Mitigation ‚Celery + Redis'. … Das ist ein interner Widerspruch zwischen zwei ADRs,
> der nirgends explizit entschieden wurde."

und zusätzlich:

> „Die Chunking-Strategie ist mindestens so wichtig für die RAG-Qualität — und fehlt
> als ADR vollständig."

→ Ergebnis: **ADR-006** (Worker auf pgqueuer, PostgreSQL-nativ, kein Redis) und
**ADR-007** (Chunking/Retrieval). Zwei ADRs entstanden aus dem Review der ersten fünf.
Das ist die beste ADR-Geschichte im ganzen Projekt — besser als die Tripwire-Story aus
Variante A, weil sie eine sichtbare Konsequenz im Betrieb hat.

**Station 10 — der Unterricht speiste direkt Code ein.**
Modul 8 (Datenfluss-Audit) → PR #126: Aufbewahrungsfristen, Pseudonymisierung,
IP-freies Zugriffslog. Aus der PR-Beschreibung:

> „Das Audit fand: bis jetzt löschte **nichts** im System jemals etwas."

Ebenso: Modul 5B baute ein Lint-Tool für die Gold-Eval-Datasets
(`Artefakten/Modul5BTag1/gold_lint.py`), die Design-Mockups aus
`Artefakten/Design-Mockups/2026-09-10-redesign/` wurden zu T-58.

### Korrektur gegenüber meiner ersten Annahme

Ich hatte vermutet, Grundgerüst und CI seien zwei Schritte gewesen. Sie sind es nicht:
**derselbe Pull Request (#6) brachte beides** — Compose-Stack, Alembic, FastAPI-Skelett,
Vite-Frontend, `ci.yml` und das CI-Runbook, 54 Dateien. Das erste Feature-Ticket wurde
danach gemergt. Für Variante B ist das die stärkere Aussage: *die Pipeline stand, bevor
das erste Feature stand.*

### Belege für Station 10 (Backend/Frontend wächst zusammen)

Die Aussage ist messbar, ich habe sie an den gemergten PRs nachgezählt:

| | PRs, die nur Backend **oder** nur Frontend berühren | PRs, die **beide** berühren |
|---|---|---|
| bis zur Spec-Umstellung (T-39) | 13 | 3 — **19 %** |
| danach | 22 | 18 — **45 %** |

Zwei Ursachen, beide belegbar:

1. **T-39 machte die Spec zur einzigen Quelle.** Seither verlangt `CLAUDE.md`, dass ein
   neuer Endpoint *im selben PR* drei Dinge mitbringt: Eintrag in `openapi.yaml`, Route
   im Backend, neu generierte Frontend-Typen. Damit ist ein Vertragswechsel technisch
   gar nicht mehr auf eine Seite beschränkt.
2. **Tickets wurden gebündelt:** T-29+T-30 · T-23+T-25+T-26 · T-33+T-34 · T-47+T-48 ·
   T-51+T-61.

> **Ehrliche Einordnung fürs Sprechen:** Die Bereichs-Trennung war eine *Planungshilfe*
> aus dem Issue-Template (Feld „Bereich: Backend/Frontend/DB/DevOps"), kein
> Architekturprinzip. Sie hat früh geholfen (klarer Scope pro Ticket) und wurde später
> teurer als ihr Nutzen. Nicht als Fehler framen, sondern als bewusste Korrektur.

### A oder B — wann was

| | Variante A (thematisch) | Variante B (chronologisch) |
|---|---|---|
| Erzählt | *wie* wir gearbeitet haben | *in welcher Reihenfolge* wir gearbeitet haben |
| Stärke | Die Rollenteilung Mensch/KI wird sehr deutlich | Der Bogen Unterricht → Projekt ist sichtbar; CI bekommt das Gewicht, das sie verdient |
| Risiko | wirkt statisch, wenig Entwicklung | 10 Stationen in 7 Minuten ist gedrängt — Folie 1 nicht vorlesen, nur zeigen |
| Passt, wenn | Block 4 stark auf Learnings geht | die Dozierenden den Modulbezug sehen sollen |

**Wenn B gewählt wird:** Folie 1 ist eine Landkarte, kein Inhalt — maximal 30 Sekunden
darauf, dann durchlaufen. Die Zeit gehört Folie 5 (CI) und Folie 6 (Takt).
