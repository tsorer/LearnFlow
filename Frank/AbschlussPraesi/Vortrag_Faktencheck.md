# Block 3 — Vortrag: Faktencheck, offene Fragen, Ergänzungen

Bezug: `Frank/AbschlussPraesi/Vortrag.txt` (Stand 2026-09-26, 515 Wörter).
Zahlen erhoben am 2026-09-26 aus GitHub (`gh`), Git-Historie, CI-Logs und dem Repo.
Jede Zahl hat unten ihre Quelle — damit sie auch in der Fragerunde hält.

---

## 1 · Bewertung in Kürze

**Was trägt:**
- Der Ablauf ist ehrlich und aus eigener Erfahrung erzählt — das ist glaubwürdiger als
  jede Methodenfolie.
- Die Länge passt: 515 Wörter sind bei ~130 Wörtern/Minute knapp 4 Minuten reine
  Sprechzeit. Bleiben ~3 Minuten für Folienwechsel, GitHub-Einblendung und Ergänzungen.
- Die Kernpunkte stimmen: Plan vor Code, Rückfragen vor Umsetzung, Selbst-Review vor PR,
  Review durch zweite Person, Rückfluss in Issues und ADRs.

**Was schwächt:**
- **Keine Pointe.** Der Text ist eine chronologische Aufzählung („zunächst … danach …
  anschliessend"). Es fehlt der eine Satz, an dem alles hängt. Der steht bereits in
  `Docs/07_Definition-of-Done.md`: *„Code wird KI-gestützt mit Claude Code erzeugt; die
  Teammitglieder sind primär Reviewer und Verifizierer."* — als Einstieg zitieren.
- **Mehrere Zahlen sind falsch oder zu tief** (37 Issues, 200 Tests, 5 Minuten, 65/64,
  „zwei oder drei Punkte") — Details in Abschnitt 2.
- **Das Beispiel fehlt** (Zeile 16). Ohne Beispiel bleibt „der Mensch entscheidet" eine
  Behauptung. Kandidaten in Abschnitt 2.11.
- **Überschneidung mit Christoph:** Ideenfindung mit vielen Feedback-Runden ist sein
  Learning 01 („Kritik ohne Stop-Kriterium", 14 Dialogrunden). Bei dir nur ein Satz,
  dann an ihn verweisen.

**Was wesentlich fehlt:**

| # | Fehlt | Warum es wichtig ist |
|---|---|---|
| 1 | **Hooks** in `.claude/settings.json` | „Keine Skills, nur CLAUDE.md" stimmt so nicht. Seit 17.06. blockieren Hooks Commit/Push auf `main` und Commits mit `.env`-Dateien; seit 05.08. (Risikoeinstufung Modul 5) darf Claude `.env` nicht lesen. **CLAUDE.md ist eine Bitte, ein Hook ist eine Regel** — genau das interessiert Dozierende. |
| 2 | **Bezug zum Unterricht** | Laut `Inhalte_Abschlusspräsentation.md` soll Block 3 den Modulbezug herstellen. Im Text fehlt er komplett. Drei belegbare Brücken: Kickoff-Vorlage (Modul 1) → Ideenfindung · Risikoeinstufung (Modul 5) → Hooks · Planner-Generator-Evaluator „kein PASS nach 2 Runden → Mensch entscheidet" (Modul 5B/6) → eure 2-Runden-Regel. |
| 3 | **Ein konkretes Beispiel** Mensch > KI | siehe 2.11 |
| 4 | **Dass CLAUDE.md mitgewachsen ist** | Nicht nur vorher verfeinert: 15 Commits, davon 10 *während* der Umsetzung (z. B. Regel „Spec und Code gehen zusammen" nach T-39). |

Optional, nur wenn Zeit bleibt: Spec-first (ADR-010) — ein Test (`tests/test_rbac.py`)
prüft Code ↔ OpenAPI-Spec in beiden Richtungen; Drift ist damit rote CI statt
Disziplinfrage.

---

## 2 · Antworten auf die offenen Fragen

### 2.1 Zeile 2 — „Verschiedene Varianten, nach diversen Feedback-Runden geeinigt" — stimmt das, belegbar?

**Teilweise.** Belegt ist:
- Kickoff 3. Mai (Modul 1 Tag 1), `Artefakten/Modul1Tag2/LearnFlow_Kickoff_Doku.md`,
  Phase 00: **drei Anwendungsbereiche** standen zur Wahl — generischer Kursfall ·
  *Entwickler:innen lernen die Fachdomäne* · *Sachbearbeiter:innen lernen die Anwendung*.
  Entscheid für Variante 1 mit vier Gründen, protokolliert im Entscheidungs-Log. Der
  stärkste Grund fürs Publikum:
  > „Halluzinationen treffen Entwickler:innen, die im Code-Review oder Sparring mit BA
  > gegenchecken können — nicht direkt Klient:innen einer Sozialberatung."
- Feedback-Runden: Claude als PO-Sparring (5 kritische Fragen), „skeptischer CTO"
  (3 Risiken), Pitch in Modul 1 Tag 2 (`LearnFlow_Pitch.pptx`), RE-Review im Mai →
  User Stories v2 → v3 (`Docs/01_UserStories.md`, Entscheide 20.05. und 10.06.).

**Einschränkung:** Es waren Varianten *einer* Idee (deiner, als PO), nicht konkurrierende
Ideen des Teams. „Wir haben uns geeinigt" ist daher etwas zu stark — „wir haben uns
entschieden" trifft es.

**Vorschlag:** ein Satz, dann an Christoph verweisen, der die Feedback-Runden als
Learning 01 zeigt:
> „Im Kickoff standen drei Einsatzbereiche zur Wahl; wir haben den gewählt, bei dem eine
> falsche Antwort noch abgefangen werden kann. Wie viele Runden das gebraucht hat,
> erzählt Christoph nachher."

### 2.2 Zeile 3 — User Stories mit MoSCoW

Stimmt. `Docs/01_UserStories.md` (v3): **11 User Stories — 5 MUST, 4 SHOULD, 2 COULD.**
Umgesetzt: alle 5 MUST und 3 von 4 SHOULD (US-06 bewusst Post-MVP), die beiden COULD nicht.

### 2.3 Zeile 4 — 10 ADRs, Anzahl stabil, Beispiele für Änderungen?

**Stimmt — mit Präzisierung.** Die Zahl 10 steht seit 03.06. (ADR-010). *Davor* wuchs sie:
Die ersten fünf ADRs (Modul 3) wurden von der KI gegengelesen; der Review fand, dass
ADR-001 „ein Deployment-Artefakt" verspricht, ADR-002 aber Celery + Redis vorsah
(`Artefakten/Modul3Tag1/ADR-Review_Kritik.md`). Daraus entstanden ADR-006 (pgqueuer statt
Redis) und ADR-007 (Chunking/Retrieval).

**Während der Umsetzung (ab 17.06.) wurden 8 der 10 ADRs nachgeführt** (nur ADR-001 und
ADR-004 nicht) — 27 Commits aus Ticket-PRs. Beispiele:

| ADR | Anlass | Was sich änderte |
|---|---|---|
| **ADR-008** Fail-closed | T-19, T-23/25/26, T-37, T-57, Issue #73 | **6 Aktualisierungsdaten im Kopf** — Quellenprüfung als Stufe 2, Reihenfolge der Unterdrückung, Schwellen in der DB validiert |
| **ADR-006** Worker | T-51 (PR #134, dein Ticket) | Nachtrag „Woher die 300 s kommen": Timeout **gemessen statt geschätzt** (Parsing 29 s, Embedding-Retry ~120 s, × 2 → 300 s) |
| **ADR-010** API-First | T-39 (PR #76), T-46 (PR #122) | OpenAPI wird *einzige* Quelle, Frontend-Typen werden generiert; Enum-Entscheid festgehalten |
| **ADR-007** Retrieval | T-50 (PR #103) | Zerrissene Wörter aus der PDF-Extraktion machten die Volltextsuche unbrauchbar |
| **ADR-009** Eval | T-47/48, T-56 | Gold-Dataset-Schema, In-Corpus-Eval |

**Für den Vortrag ein Beispiel:** ADR-008 „sechsmal nachgeführt" als Zahl + T-51 als
Geschichte (Messung → Wert → Nachtrag im ADR). Issue #73 (fail-closed war fail-open)
**nicht** verwenden — das ist Christophs Learning 03.

### 2.4 Zeile 5 — CLAUDE.md verfeinert, „welche Verzeichnisse ignoriert werden können"

Präzisieren: Das Ausblenden macht die **`.claudeignore`** (PR #50, 17.06.:
`Niklaus/ Reto/ Frank/ Christoph/ Artefakten/`). CLAUDE.md verweist darauf und hält als
Tripwire fest, dass Spike-Verzeichnisse und `Artefakten/` keine Quelle der Wahrheit sind.

CLAUDE.md-Historie: **15 Commits** — 5 vor der Umsetzung (06.05.–24.06., darunter
„Implementierungs-Phase" #46, „Arbeitsweise-Sektion" 17.06., „Entwicklungsprozess + DoD"
#56), **10 während der Umsetzung**. Also: vorher verfeinert *und* laufend nachgeschärft.

### 2.5 Zeile 6 — Reto hat das Repo erstellt, Access-Token

Repo `tsorer/LearnFlow`, Initial Commit 06.05. durch `tsorer` — passt. Die Token-Vergabe
pro Person lässt sich aus dem Repo nicht belegen (liegt ausserhalb); so stehen lassen.

### 2.6 Zeile 7 — „initial 37 Issues, 120 Story Points"?

**Korrektur: 38 Issues (T-01 … T-38), 127 Story Points.**
- Alle 38 am **10.06. an einem Tag** per Skript angelegt (`Reto/Modul4Tag1/create-issues.ps1`),
  mit Milestone und **DoD-Checkliste in jedem Issue-Body** (7 Punkte).
- Am selben Tag gab es noch ein Issue „Test" (#7) — daher zeigt GitHub 39 Issues vom 10.06.
- Summe 127 SP aus dem Skript nachgerechnet (1/2/3/5er-Punkte).
- Seit PR #47 (17.06.) stehen Story Points nur noch im Project Board, nicht mehr im Issue.

### 2.7 Zeile 8 — Wochensprints, „20 SP pro Woche im grünen Bereich", Übersicht?

**Wochensprints ab Sprint 3.** Milestones in GitHub: Sprint 0 und 1 bis 24.06., Sprint 2
bis 05.08. (Sommerpause), **Sprint 3 bis 8 jeweils eine Woche** (05.08.–15.09.).
Team-Vorgabe: keine Daten zeigen — also nur „ab Sprint 3 im Wochentakt" sagen.

Story Points laut **Project Board „LearnFlow Sprint Board"** (Stand 26.09., von dir
geliefert): **Done 60 Issues · 175 SP**, Todo 7 Issues · 0 SP.

| Sprint | S0 | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 |
|---|---|---|---|---|---|---|---|---|---|
| Story Points | 6 | 15 | 8 | **24** | **20** | **30** | **18** | **22** | **32** |
| Issues | 2 | 6 | 2 | 9 | 7 | 9 | 8 | 10 | 8 |

(+ 6 Issues ohne Milestone, 0 SP.)

→ Wochensprints S3–S8: **Ø 24 SP pro Woche** (Spanne 18–32), **in 5 von 6 Wochen
mindestens 20 SP**. Deine Aussage „bei 20 SP pro Woche im grünen Bereich" hält also — die
Marke wurde nur in Sprint 6 knapp verfehlt (18).
→ Erstplanung 127 SP (38 Issues) → am Ende **175 SP erledigt** (60 Issues).

### 2.8 Zeile 9 — CI von Anfang an mit Backend-, Frontend- und E2E-Tests? 200 Tests, 5 Minuten?

**Teilweise — und die Zahlen sind viel besser als gedacht.**

Zeitlinie (`git log -- .github/workflows/ci.yml`):
- **10.06.** PR #6 „CI-Pipeline": Jobs `backend` + `frontend` — das Grundgerüst stand
  *vor* dem ersten Feature-Ticket.
- **17.06.** CI V2: Backend `ruff` + `mypy` + `pytest`, Frontend `eslint` + `tsc` + `vitest`.
- **09.08.** Job **`e2e`** kommt dazu (T-09, PR #61) — also nicht von Anfang an.
- **12.08.** T-41: alle drei als **Required Checks** mit Branch Protection. Erst ab hier ist
  „nur grün wird gemergt" technisch erzwungen, vorher war es Absprache.

Stand heute (CI-Lauf vom 24.09.):

| | Tests | Dauer |
|---|---|---|
| Backend (`pytest`) | **688** | Testlauf selbst 6,6 s |
| Frontend (`vitest`) | **173** in 13 Dateien | |
| e2e gegen den ganzen Stack | **63** | |
| **Summe** | **924** | **ein CI-Lauf ≈ 2 Minuten** (Jobs parallel, e2e am längsten) |

Weitere belastbare Zahlen: **303 CI-Läufe, davon 15 rot** — weil `make qa` laut DoD schon
lokal vor jedem PR lief. Und: **mehr Testcode als Produktivcode** (siehe 2.12).

Formulierungsvorschlag:
> „Die Pipeline stand, bevor das erste Feature stand. End-to-End-Tests kamen im August
> dazu, seither kann kein roter PR mehr gemergt werden. Heute sind es über 900 Tests,
> ein Lauf dauert zwei Minuten."

### 2.9 Zeile 13 — „zwei oder drei Punkte" beim Selbst-Review

Tippfehler („drei oder drei") und zu tief gegriffen. In deinen exportierten Verläufen
(`Frank/Prompts/`) hatten die Pre-Reviews: T-13 → 2 · T-19 → 3 (+2 Kleinigkeiten) ·
T-32 → 3 · T-17 → 6 (+4) · T-51 → 6 · T-18 → 7 · T-57 → 10 · T-42 → 11+ (du: „fix alle
bis auf #9 und #11") · T-56 → 15.
→ **„Je nach Grösse zwischen drei und fünfzehn Befunde."**

Wichtiger als die Zahl ist, was danach passierte: Du hast fast nie „fix alles" gesagt,
sondern **„bewerte"** (27-mal in deinen Prompts). Beispiel PR #76:
> „Wie schwerwiegend sind die Befunde? Was passiert, wenn es nicht angepasst wird?"

### 2.10 Zeile 14 — Reviews der anderen fanden immer etwas; Beschränkung auf 2 Runden

Belegt:
- **51 von 57 Feature-PRs** hatten substanzielles schriftliches Feedback von jemand
  anderem als dem Autor (Review mit Befunden oder PR-Kommentar > 80 Zeichen). Die
  übrigen 6 sind Kleinst-PRs (#53, #72, #83, #108, #112, #114).
- Viele Befunde kamen als **„Approve mit Anmerkungen"** (z. B. #104: Approve mit 6 000
  Zeichen Befunden) — 12 PRs bekamen formell „Changes requested".
- Zwei Runden: PR #86 (T-19) „zwei Review-Runden von zwei Reviewern", ebenso #117, #119, #139.
- Die 2-Runden-Regel ist **gelebte Praxis, nirgends festgeschrieben** — so sagen.

**Brücke zum Unterricht:** Das Planner-Generator-Evaluator-Muster aus Modul 5B/6
(`Frank/Modul5BTag2/test_pge.py`) endet genau so:
`kein PASS nach 2 Runden -> Mensch entscheidet`. Ihr habt dieselbe Regel auf
Menschen-Reviews übertragen. **Achtung:** Warum Kritik ein Stop-Kriterium braucht, ist
Christophs Learning 01 — du nennst nur die Regel, er liefert das Warum.

### 2.11 Zeile 16 — Beispiel, wo du etwas gesehen hast, das Claude übersehen hatte

**Entscheid (26.09.): Beispiel B — T-15.** Es steht in Variante D auf Folie 6; Zitat A („kantonal unterschiedlich") ist als O-Ton auf Folie 5.
Die anderen beiden bleiben als Reserve für die Fragerunde.

**A — Gold-Dataset „CHF 1061" (Fachwissen) — Reserve.**
`Frank/Prompts/2026-08-31_T-47-T-48-Gold-Eval-Dataset-PR-101.md`
- Im Gold-Dataset — also genau den Fragen, an denen wir Halluzinationen messen — stand:
  *„Wie hoch ist der Grundbedarf für einen 1-Personen-Haushalt?"* → Referenzantwort
  *„CHF 1061 pro Monat"*, Kategorie „im Korpus beantwortbar".
- Du: *„Die Höhe ist aber nicht in den SKOS-Richtlinien angegeben, oder?"*
- Claude bestätigte das — und erklärte es mit einer **Vermutung**: die Tabelle liege
  wohl als Grafik vor. Später selbst eingeräumt: „Meine ‚Grafik'-Erklärung war eine
  Vermutung, mit der ich das Fehlen erklärt statt es benannt hatte."
- Du: *„Der Betrag ist kantonal unterschiedlich, daher gibt es in den Richtlinien keine
  Beträge."* → Die richtige Antwort des Systems ist „Weiss ich nicht".
- **Pointe:** Ohne diese Korrektur hätte unsere eigene Eval eine Halluzination als
  richtige Antwort belohnt. Beim anschliessenden Durchgehen aller Fragen: **7 sachlich
  falsche Einträge korrigiert** (PR #101).
- **Absprache mit Niklaus nötig:** Block 5 hat die Folie „Gold muss Gold sein" (3 von 80
  Fragen „eher Bronze"). Das ist kein Konflikt, sondern eine Brücke: du zeigst den Fall,
  er die Konsequenz. Kurz abstimmen, damit er nicht dasselbe Beispiel bringt.

**B — T-15, PR #87: die Fragen, die Claude nicht gestellt hat — gewählt.**
`Frank/Prompts/2026-08-24_T-15-Versionierung-PR-87.md`. Claude hatte umgesetzt, Tests
grün; drei Rückfragen von dir, keine davon von Claude angestossen:

1. **Klartext-Passwörter:** *„in test_documents_replace.py sind Benutzername/Passwort in
   Klartext … Passwörter gehören meiner Meinung nach nicht in GIT"* → Das Muster war
   älter (Seed-Skript, README, zwei bestehende e2e-Tests). Ergebnis: alle drei e2e-Tests
   (`test_documents_replace`, `test_login_flow`, `test_documents_cascade`) lesen die
   Zugangsdaten aus `seed_users.py` bzw. aus `E2E_OWNER_*`-Umgebungsvariablen.
2. **Status als freier Text:** *„du schreibst direkt document.status = "pending". Sollte
   nicht irgendwo die Liste definiert sein …?"* → Die Liste stand nur in der Spec. Darum
   war schon einmal ein Default durchgerutscht, den die Spec nicht kennt: `queued`
   (Migration 0003, korrigiert in 0006). Ergebnis: `DocumentStatus`-Enum in
   `models/tables.py`; `tests/test_openapi_spec.py` schlägt an, sobald Spec und Enum
   auseinanderlaufen.
3. **Folge-Issue statt Fix:** *„Kannst du das nicht auch gleich hier beheben? Wieso wäre
   ein Folge-Issue besser?"* → Claude räumte ein, dass die Lücke erst durch T-15 entsteht;
   im selben PR behoben (Versions-Guard im Worker, drei neue Tests).

**Achtung Fragerunde:** Zwei *parallel* entstandene PRs — T-37 (#89) und T-45 (#91),
gemergt am 23./24.08., also zeitgleich mit T-15 — brachten Seed-Passwörter zurück
(`e2e/test_admin_config_endpoint.py`, `e2e/test_query_rate_limit.py`). Auf der Folie
steht deshalb bewusst nur „alle **drei** e2e-Tests", nicht „kein Passwort mehr in e2e".
Falls jemand nachfragt, ist das eine ehrliche Pointe: *Was nur im Chat einer Person
entschieden wird, gilt nicht fürs Team — dafür braucht es CLAUDE.md oder einen Hook.*
Ausserdem hast du später selbst festgehalten: Klartext-Passwörter in `seed_users.py` und im
README sind für den Dev-Stack akzeptabel (Pilotstart-Checkliste verlangt den Ersatz).

**C — Der Mensch als Langzeitgedächtnis — Reserve.**
`Frank/Prompts/2026-08-19_T-17-Query-Retrieval.md`:
> „Es muss pro IP-Adresse sein, da man sonst zu einfach Benutzer aussperren kann.
> (Haben wir schon mal ausdiskutiert)."

Claude hat pro Session kein Gedächtnis über Wochen — das Team schon.

*Nicht* verwenden: PR #60 (T-14, „Lautet die Anforderung nicht, dass das Dokument
geliefert werden soll?") — dort lag Claude richtig und hat es mit vier Belegen gezeigt.
Taugt höchstens als Gegenbeispiel „Rückfrage statt Befehl".

### 2.12 Zeile 17/18 — „65 Issues und 64 PRs"? Übersicht Issues, PRs, Lines of Code

**Issues** (GitHub, 26.09.)

| | |
|---|---|
| Issues gesamt | **69** (62 geschlossen, 7 offen) |
| davon Test-Issue #7 | 1 |
| **geplant** am 10.06. | **38** (T-01 … T-38) |
| **unterwegs entstanden** | **30** (T-39 … T-65 + 3 ungenummerte: #73, #74, #92) |
| offen | T-53, T-59, T-60, T-62, T-64, T-65 — bewusst zurückgestellt (Block 5) · T-61 ist mit PR #134 umgesetzt, das Issue nur nicht geschlossen |

→ Sprechsatz: **„Aus 38 geplanten wurden 68 Tickets — 30 sind unterwegs entstanden."**

**Pull Requests**

| | |
|---|---|
| PRs gesamt | **78**, davon **75 gemergt** |
| Feature-/Ticket-PRs | **57** |
| Setup, Docs, CLAUDE.md, CI | 12 |
| Präsentation / Kursdoku | 6 |
| nicht gemergt | 3 |

**Codeumfang** (`git ls-files … | wc -l`, Zeilen inkl. Kommentare)

| Bereich | Zeilen |
|---|---|
| Backend (`app/`, `worker/`) | 6 349 |
| Frontend (`src/`, ohne generierte Typen und Tests) | 4 040 |
| **Produktivcode** | **≈ 10 400** |
| Backend-Tests + e2e | 11 645 |
| Frontend-Tests | 3 406 |
| **Testcode** | **≈ 15 050** |
| Alembic-Migrationen (20 Stück) | 2 130 |
| OpenAPI-Spec | 1 709 |
| `Docs/` (Markdown) | 3 227 |

→ **Pointe: 1,45 Zeilen Test pro Zeile Produktivcode.** Das ist die Zahl, die zu „die
KI schreibt, wir verifizieren" passt.

---

## 3 · Überarbeiteter Sprechtext (7 Folien, ≈ 610 Wörter ≈ 4,7 Min bei 130 Wörtern/Min)

Folienmarker `[F1]` … `[F7]` passen zu Variante D (Abschnitt 4). Mit 7 Folien bleibt
nur Zeit, wenn der Text knapp ist — die Folien tragen die Details, gesprochen wird nur
die Aussage.

> **[F1 — Erst entscheiden, dann bauen]**
> Nach der Live-Demo und dem Blick in die Pipeline zeige ich, *wie* wir LearnFlow gebaut
> haben. Vorweg der Leitsatz aus unserer Definition of Done: „Code wird mit Claude Code
> erzeugt; die Teammitglieder sind primär Reviewer und Verifizierer." Selbst geschrieben
> haben wir keinen Code — wir haben entschieden und geprüft.
> Im Kickoff standen drei Einsatzbereiche zur Wahl; wir haben den gewählt, bei dem eine
> falsche Antwort noch abgefangen werden kann. Wie viele Runden das gebraucht hat,
> erzählt Christoph. Daraus wurden elf User Stories nach MoSCoW, zehn
> Architekturentscheide und schliesslich 38 Issues — jeder Schritt aus einem Kursmodul.
>
> **[F2 — Eine CLAUDE.md ist eine Bitte. Ein Hook ist eine Regel.]**
> Vor der ersten Zeile Code haben wir die CLAUDE.md für die Umsetzung umgeschrieben:
> Massgeblich ist der Ordner Docs, der Entwicklungsprozess gilt für jedes Issue, und
> Stolperdrähte wie „Fail-closed-Schwellen nie aufweichen" sind festgeschrieben.
> Kurs-Verzeichnisse blendet eine .claudeignore aus. Skills haben wir keine gebaut. Aber
> eine CLAUDE.md ist nur eine Bitte — deshalb blockieren Hooks jeden Commit oder Push auf
> main und jede .env-Datei. Und die CLAUDE.md ist mitgewachsen: Zwei Drittel ihrer
> Änderungen kamen erst während der Umsetzung.
>
> **[F3 — Die Pipeline stand vor dem ersten Feature]**
> Reto hat das GitHub-Repository aufgesetzt, jede und jeder hat Claude per Access-Token
> Zugriff gegeben. Die 38 Issues haben wir an einem Tag per Skript angelegt, mit
> 127 Story Points und der Definition of Done als Checkliste in jedem Ticket. Ab Sprint 3
> arbeiteten wir im Wochentakt; 20 Story Points waren die Marke, im Schnitt wurden es 24.
> Eines der ersten Tickets war die CI. Seit Sprint 3 sind alle drei Jobs Pflicht — ein
> roter PR kann nicht gemergt werden. Heute: über 900 Tests, zwei Minuten pro Lauf, und
> mehr Testcode als Produktivcode.
>
> **[F4 — Erst Rückfragen, dann Code]**
> Jedes Ticket lief durch denselben Zyklus. Mein Standard-Prompt: „Erstelle einen
> Umsetzungsplan für Issue XY — und stelle mir vor der Umsetzung Fragen, bis alle
> Unklarheiten geklärt sind." Claude liefert also zuerst Rückfragen, keinen Code. Vor dem
> PR lief ein Selbst-Review mit drei bis fünfzehn Befunden; die zweite Person fand
> trotzdem fast immer noch etwas. Ab der dritten Runde waren es nur noch Kleinigkeiten —
> deshalb höchstens zwei Runden, wie beim Planner-Generator-Evaluator aus dem Unterricht.
> Parallel lief meist eine zweite Session für Reviews, in getrennten Worktrees.
>
> **[F5 — Der Mensch entscheidet, wörtlich]**
> Wie das konkret klingt, zeigen meine Chatverläufe: Die meisten Prompts waren keine
> Aufträge, sondern Entscheide. Beim Review etwa: „Wie schwerwiegend sind die Befunde? Was
> passiert, wenn es nicht angepasst wird?" Oder die Triage: „Ja, fix alle bis auf neun und
> elf." Und manchmal hat nur der Mensch das Wissen: „Der Betrag ist kantonal
> unterschiedlich" — das steht in keinem unserer Dokumente.
>
> **[F6 — Die Fragen, die Claude nicht gestellt hat]**
> Ein Beispiel im Detail, mein eigenes Ticket zur Versionierung. Claude hatte umgesetzt,
> die Tests waren grün. Mir sind trotzdem zwei Dinge aufgefallen, die Claude nicht
> angesprochen hatte. Erstens: Klartext-Passwörter in den End-to-End-Tests — die gehören
> nicht ins Git. Zweitens: Der Status eines Dokuments stand als freier Text im Code. Meine
> Frage, ob die Liste nicht irgendwo definiert sein sollte, deckte auf: Sie stand nur in
> der API-Spec — deshalb war schon einmal ein falscher Standardwert durchgerutscht. Heute
> gibt es eine Aufzählung im Code und einen Test, der Spec und Code abgleicht.
> Claude beantwortet Fragen sehr gut. Welche Fragen man stellen muss, bleibt unsere
> Aufgabe.
>
> **[F7 — 38 geplant. 30 kamen dazu.]**
> Solche Funde gingen zurück in Issues und ADRs: Aus 38 geplanten wurden 68 Tickets, acht
> der zehn ADRs wurden unterwegs nachgeführt. Und auch den Backlog selbst haben wir
> korrigiert. Anfangs gab es pro Feature ein Backend- und ein Frontend-Ticket. Seit die
> API-Spec die einzige Quelle ist, gehören Spec, Backend und generierte Typen in denselben
> PR — also haben wir Tickets gebündelt. Vorher berührten 13 Prozent der PRs beide Seiten,
> danach 45. Die Trennung war eine Planungshilfe, kein Architekturprinzip.
> Nicht alles lief also nach Plan. Was uns der Prozess gekostet hat und was wir gelernt
> haben — dazu jetzt Christoph.

---

## 4 · Variante D — umgesetzt (26.09.)

Datei: `Frank/AbschlussPraesi/Block3_Umsetzung_VarianteD.html`, integriert als
`Artefakten/Abschlusspräsentation/Block3_Umsetzung.html` (Block 5 von 7 in
`Gesamtpraesentation.html`; die vorherige Kopie war identisch mit Variante B, die in
`Frank/AbschlussPraesi/` erhalten bleibt).

**D folgt dem Sprechtext** — chronologisch vom Kickoff zum Merge, mit dem Zyklus aus C
als Herzstück, einer O-Ton-Folie für die Breite, einem Beispiel für die Tiefe und der
Bündelung aus Variante B als Überleitung zu Christoph. Gleiche Formensprache wie A–C
(1600×900, Tokens aus Christophs Folien), 7 Folien à ~50 s.

| # | Folie | Titel | Inhalt | übernimmt aus |
|---|---|---|---|---|
| 1 | Vom Kickoff zum Backlog | „Erst entscheiden, dann bauen" | 3→1 Einsatzbereiche → 11 User Stories → 10 ADRs → 38 Issues / 127 SP, je mit Modulbezug (Modul 1–4) · DoD-Leitsatz | neu |
| 2 | Das Regelwerk | „Eine CLAUDE.md ist eine Bitte. Ein Hook ist eine Regel." | 3 Ebenen: CLAUDE.md · `.claudeignore` · Hooks + Leseverbot `.env` (Modul 5) | neu |
| 3 | Takt & Sicherheitsnetz | „Die Pipeline stand vor dem ersten Feature" | Sprint-Leiste (ab S3 wöchentlich, Ø 24 SP, 175 SP erledigt) · 3 Required Checks mit Testzahlen · 924 Tests · ≈ 2 Min · 15/303 rot | B (Folie 5) |
| 4 | Ein Ticket, ein Zyklus | „Erst Rückfragen, dann Code" | Kreis (8 Stationen) + Standard-Prompt + bewerten statt fixen + 51/57 PRs mit Befunden + max. 2 Runden (PGE, Modul 5B) + Worktrees | C (Folie 2+3) |
| 5 | O-Ton | „Der Mensch entscheidet — wörtlich" | 6 Zitate aus `Frank/Prompts/`, je mit Station im Zyklus: Rückfrage entscheiden (T-49) · Befunde gewichten (PR #76) · Triage (T-42) · Backlog sauber halten (T-23) · Review-Regel (PR #93) · Fachwissen (T-47) | neu |
| 6 | Beispiel | „Die Fragen, die Claude nicht gestellt hat" | T-15 / PR #87: Klartext-Passwörter · Status als freier Text · Folge-Issue statt Fix (nur Folie, nicht gesprochen) | neu |
| 7 | Rückfluss + Bündelung | „38 geplant. 30 kamen dazu." | Balken 38/30 · Spec als einzige Quelle + gebündelte Tickets (T-29+30, T-23+25+26, T-33+34, T-47+48, T-51+61) · 13 % → 45 % · Übergabe an Christoph | B (Folie 7), C (Folie 4) |

**Warum 7 und nicht 8 Folien:** Eine eigene Bündelungs-Folie hätte 8 Folien in
7 Minuten bedeutet. Rückfluss und Bündelung erzählen dasselbe — der Backlog passt sich
an — und stehen deshalb zusammen auf der Schlussfolie. Dafür sind die Kacheln der
früheren Folie 6 umgezogen: 175 SP → Folie 3, 51/57 PRs → Folie 4, 8/10 ADRs → linke
Spalte von Folie 7; das T-46-Beispiel ist entfallen.

**Korrektur gegenüber Variante B:** B nennt „19 % → 45 %". Nachgerechnet über alle
gemergten PRs, die `src/backend` oder `src/frontend` berühren (26.09.): **bis und mit
T-39 (#76) 2 von 15 = 13 %**, **danach 18 von 40 = 45 %**. Die 19 % liessen sich nicht
reproduzieren; auf der Folie stehen 13 %.

Navigation: Pfeiltasten/Leertaste innerhalb des Blocks; **nach Folie 7 geht → direkt zu
Block „Herausforderungen & Learnings"**, vor Folie 1 geht ← zurück zu „Technischer Aufbau".
`,` und `.` wechseln den Block auch dann, wenn der Fokus im Block liegt. Im
Einzelaufruf (ohne Gesamtpräsentation) laufen die Folien im Kreis wie bei A–C.
Getestet über einen lokalen Server in der Gesamtpräsentation.

**Tipp für den Vortrag:** Die Folien 3 und 6 tragen ein „live in GitHub"-Abzeichen
(Milestones, PR #87). Tabs vorher öffnen, Zoom ~150 %, pro Wechsel max. 30 s — oder
einfach nicht umschalten, die Folie trägt die Aussage auch allein.

---

## 5 · Offene Punkte / nicht belegbar

- **Access-Token pro Person** — nicht aus dem Repo belegbar.
- **Absprachen:** Ideenfindung und 2-Runden-Regel mit Christoph (Block 4, Learning 01) —
  und dass Folie 7 mit „Nicht alles lief nach Plan" an ihn übergibt. Das O-Ton-Zitat
  „kantonal unterschiedlich" (Folie 5) berührt Niklaus' Folie „Gold muss Gold sein"
  (Block 5) — kurz Bescheid geben, damit er es als Rückverweis nutzen kann.
- **Zeit:** Sprechtext ≈ 610 Wörter (≈ 5 Min) + 7 Folienwechsel ≈ 6 Min. Puffer für einen
  GitHub-Wechsel ist da; mehr als einer wird knapp.
- **GitHub-Hygiene:** PR #134 sagt „Schliesst T-51 und T-61", Issue #132 (T-61) steht
  aber noch auf *offen* (kein `Closes #132` im PR). Vor der Präsentation schliessen, sonst
  passt die Bündel-Chip „T-51 + T-61" nicht zum Board.
- **Zahlen vor der Präsentation nachziehen** — falls noch PRs gemergt werden.
