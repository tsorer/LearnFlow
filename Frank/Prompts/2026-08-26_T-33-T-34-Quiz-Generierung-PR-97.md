# Chatverlauf — T-33 / T-34 Quiz-Generierung und Review-Schema

**Datum:** 2026-08-26 (Export 2026-08-31)
**Branch:** `feat/T-33-T-34-quiz-generierung`, von `origin/main` angelegt. Ein Commit (`9c91bfe`), gesquasht vor dem PR.
**Gegenstand:** [#40](https://github.com/tsorer/LearnFlow/issues/40) „[T-33] FastAPI: POST /quiz/generate", [#41](https://github.com/tsorer/LearnFlow/issues/41) „[T-34] DB: quiz_questions-Tabelle" (Sprint 6, US-07 / US-08) — gemeinsam umgesetzt, wie es die Backlog-Durchsicht vom 2026-08-16 in beiden Issues vorgeschlagen hatte.
**Ergebnis:** [PR #97](https://github.com/tsorer/LearnFlow/pull/97), approved, CI grün (`backend`, `frontend`, `e2e`), gemergt am 2026-08-27 als `66c06b3`. Beide Issues geschlossen. Nebenprodukt: Metadaten-Korrektur in [#42](https://github.com/tsorer/LearnFlow/issues/42) und [#43](https://github.com/tsorer/LearnFlow/issues/43).

> Nutzer-Prompts wörtlich aus dem Sitzungstranskript. Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> Erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/40 und https://github.com/tsorer/LearnFlow/issues/41 (T-33 und T-34 sollen zusammen umgesetzt werden)

### Claude

**Zwei Funde, die den Zuschnitt der Aufgabe verändert haben.**

Erstens: **Die Tabelle `quiz_questions` existierte bereits** — Migration `0005_quiz.py`, Modell `tables.py:177`, im ERD als „⬜ T-34, nicht im aktuellen Sprint" geführt. Sie war aber auf Verdacht geschnitten und erfüllte die Akzeptanzkriterien von T-34 nicht: `approved` als Boolean statt des geforderten dreiwertigen Status, und kein Bezug zur Quellen-Passage. Damit war T-34 eine **ALTER-Migration**, keine neue Tabelle — und `0005` durfte nicht editiert werden, weil die Revision auf jeder bestehenden DB gelaufen ist (Begründung analog `0012`).

Zweitens: Der Kommentar in `documents.py:226` verwies ausdrücklich auf dieses Ticket. Seit T-15 ersetzt ein Upload mit gleichem Dateinamen das Dokument und löscht die Chunks der alten Fassung — die Frage, was dabei mit den Quiz-Fragen passiert, war auf T-33 vertagt worden. Sie liess sich nicht umgehen, weil sie die FK-Semantik von `chunk_id` bestimmt.

**Gelesen:** beide Issues samt Kommentaren, dazu #42 / #43 als Folgetickets; US-07 / US-08 in `01_UserStories.md` und `02_Requirements.md`; ADR-008 vollständig; `08_ERD.md`; `07_Definition-of-Done.md`; `generation.py`, `retrieval.py`, `documents.py`, `limiter.py`, `openapi.yaml`, `test_openapi_spec.py`, `test_rbac.py`.

Drei Entscheide waren nicht aus Issue oder Docs ableitbar und wurden dem Nutzer vorgelegt: die Replace-Semantik, der Umfang des Schemas (nur T-34 oder zusätzlich `approved_at` / `explanation` aus US-07 / US-08) und das Verhalten bei einem unbrauchbaren LLM-Ergebnis.

---

## 2 — Nutzer *(Antwort auf die drei Fragen)*

> **Replace:** Idee: Die Frage soll erhalten bleiben, aber die Freigabe wird entzogen. Es muss neu geprüft werden, ob die Frage mit der neuen Dateiversion noch zulässig ist. Falls nicht löschen, ansonsten kann Stefan sie wieder freigeben. Kann das so umgesetzt werden?
>
> **Schema-Umfang:** + approved_at + explanation
>
> **Validierung:** Ungueltige verwerfen, Rest speichern

### Claude

Ja — und die Antwort auf die erste Frage legte die FK-Semantik fest, die vorher offen war:

- `chunk_id` wird **`ON DELETE SET NULL`**, nicht CASCADE. CASCADE hätte die Frage mit ihrem Chunk gelöscht, also genau das Gegenteil des Gewünschten.
- Weil die Chunks beim Replace verschwinden und der Worker neue mit neuen IDs schreibt, ist die Verknüpfung danach nicht wiederherstellbar. Deshalb kam **`source_excerpt`** als Snapshot der Passage dazu — sonst hätte Stefan beim erneuten Prüfen nichts mehr vor sich (US-07 verlangt „inklusive der Quellen-Passage").
- Der NULL-Wert ist damit gleichzeitig die **Markierung „stammt aus einer ersetzten Fassung"**, weil eine frisch generierte Frage immer einen Chunk hat. Kein zusätzliches Flag nötig.
- **Nur `approved` → `pending`.** Bereits abgelehnte Fragen bleiben abgelehnt; sie erneut vorzulegen wäre Arbeit, die Stefan schon erledigt hat.

Damit stand der Plan: Migration `0016`, Service `quiz.py`, Chunk-Stichprobe in `retrieval.py`, Router, Spec zuerst, Docs, Tests.

---

## 3 — Nutzer *(Rückfrage im Plan, Freigabe zurückgehalten)*

> Zu „Genug Auswahl für 5 Fragen aus verschiedenen Quellen, ~5k Kontext-Tokens":
> werden 10 Fragen erstellt und dann 5 verworfen oder was ist die Idee von Sample_Size?

### Claude

Missverständliche Formulierung im Plan — `SAMPLE_SIZE` zählt **Chunks, nicht Fragen**. Es werden 10 Chunks aus dem Bereich gezogen und als nummerierter Kontext in einen einzigen LLM-Aufruf gegeben; daraus entstehen 5 Fragen. Nichts wird auf Vorrat erzeugt und weggeworfen.

Der Grund für 10 statt 5: Das Modell soll unter den Abschnitten *auswählen* können. Bei genau 5 Chunks müsste es aus jedem eine Frage pressen, auch aus einem Inhaltsverzeichnis oder einer Übergangspassage. Die Zahl ist gleichzeitig die Obergrenze für die Kontextlänge (~5k Tokens).

Plan an der Stelle präzisiert, danach freigegeben und umgesetzt.

---

## 4 — Umsetzung *(ohne eigenen Prompt, im Anschluss an die Freigabe)*

### Claude

**Spec zuerst** (ADR-010): Tag `quiz`, Pfad `/api/quiz/generate` mit den Codes 201 / 401 / 403 / 409 / 429 / 503, Schemas `QuizQuestionStatus`, `QuizQuestion`, `QuizGenerationResponse`. Danach Route, dann Typgenerierung und `schema.d.ts` im selben Commit.

**Migration `0016_quiz_review_schema`:** `chunk_id` (FK, `ON DELETE SET NULL`), `source_excerpt`, `explanation`, `status` mit `CHECK` auf die drei Werte, `approved_at`. Backfill `status = CASE WHEN approved THEN 'approved' ELSE 'pending' END` vor dem Drop der Boolean-Spalte — korrekt auch ohne die Annahme, die Tabelle sei leer. Zweiter `CHECK` auf `jsonb_array_length(options) = 4`, weil „4 Optionen" ein Akzeptanzkriterium ist.

**`services/quiz.py`:** Erster Aufrufer mit `response_format` als JSON-Objekt im Projekt. `parse_quiz_response` als reine Funktion getrennt vom Provider-Aufruf, damit die Komponente ohne LLM testbar ist (DoD 3). Verworfen wird jede Frage mit falscher Optionsanzahl, leerer oder doppelter Option, `correct_answer` ausserhalb A–D, oder einer Quellen-Nummer, die es nicht gibt — letzteres mit derselben Begründung wie `citation_invalid` in ADR-008.

**`services/retrieval.py`:** `sample_chunks` mit zufälliger Reihenfolge, wiederverwendet `_VISIBLE` — was Quiz-Fragen sehen dürfen, ist dieselbe Menge, die Antworten belegen darf. `render_context` aus `generation.py` bekam ein schmales `Protocol` als Parametertyp, damit Quiz-Chunks ohne Score nicht als `RetrievalHit` mit genullten Rängen getarnt werden müssen.

**`documents.py`:** Der vertagte Kommentar wurde durch die Entscheidung *und* ihre Umsetzung ersetzt (`UPDATE` auf `pending`, nur für freigegebene Fragen).

**Docs:** ERD-Block, Beziehung zwischen `chunks` und `quiz_questions`, Migrationstabelle; ADR-008-Nachtrag mit der Begründung, warum die Konfidenz-Pipeline hier nicht mitläuft.

**Zwei Mängel, die erst der manuelle Durchlauf gegen den echten Provider zeigte** — kein Test hätte sie gefunden:

1. **Alle fünf richtigen Antworten waren `A`.** Lara hätte mit „immer die erste" 5/5 erreicht; das Quiz hätte Raten gemessen statt Verständnis (US-08).
2. Das Modell schrieb den Buchstaben zusätzlich in den Optionstext — er wäre in der UI doppelt erschienen.

Behoben über zwei zusätzliche Prompt-Regeln und ein deterministisches Strippen des Präfixes. Nach dem Fix: Verteilung A×1 / B×4, Optionen ohne Präfix.

Ergebnis: 17 Dateien, +1888 Zeilen, ein Commit.

---

## 5 — Nutzer

> bewerte diese Findings:
>
> **Findings**
>
> * `src/backend/app/services/quiz.py:222` — Option-label stripping discards the model's own letter while `correct_answer` is still resolved by list position; a labelled-but-reordered `options` array stores an inverted answer key that passes every validation rule.
> * `src/backend/app/services/quiz.py:264` — `_finish_reason` runs before `_content_from`, so the latter's `getattr(response, "choices", None)` guard is unreachable; a response without `choices` raises `AttributeError` → 500 instead of the documented 503. `generation.py:176` orders these the other way round.
>
> Only the first is worth acting on before merge, and it's a three-line guard in `_read_question`: if all four options carry a label, require them to read A–D in order, else `_discard`.
>
> **Not findings, but worth a note**
>
> * T-33 AK "5 Fragen werden generiert" is deliberately met as "up to 5" — documented in the 201 description and in `test_generated_counts_the_rows_that_were_written`. Fine, but call it out in the PR so the reviewer signs off on the deviation rather than discovering it.
> * `QUIZ_RATE_LIMIT` has no test. `test_rate_limit.py` covers `/query` only and doesn't enumerate limited routes, so nothing would catch the decorator being dropped.
> * Repeated clicks produce duplicates — nothing dedups questions within a run or across runs. Stefan sees them in the queue, so it's a product cost, not a defect.

### Claude

**Beide Findings am Code geprüft und bestätigt, beide behoben.**

**Finding 1 war der einzige echte Korrektheitsfehler** — und der schärfste Teil war, dass die eigene Normalisierung das Problem *unsichtbarer* gemacht hatte als vorher. `correct_answer` wird über die Listenposition aufgelöst; die Buchstaben des Modells waren eine zweite, konkurrierende Zuordnung. Beschriftete, aber umsortierte Optionen hätten einen **invertierten Antwortschlüssel** gespeichert, der jede Regel passiert — und das Strippen hätte den einzigen Beleg dafür entfernt. Umgesetzt mit einer Erweiterung gegenüber dem Vorschlag: das Regex fängt den Buchstaben als Gruppe, und eine **teilweise** beschriftete Liste wird ebenfalls verworfen — die widerspricht der Reihenfolge per Definition.

**Finding 2 trotz der Einschätzung „nicht mergeblockend" mitgenommen.** Nicht aus Ordnungsliebe: Es ist eine Zeile, und der Unterschied ist im Verhalten sichtbar. Eine Antwort ohne `choices` ergab `AttributeError` → vom Router bewusst als 500 durchgereicht, während `openapi.yaml` für genau diesen Fall 503 zusagt. Ein unerreichbarer Guard plus eine Spec, die etwas anderes verspricht, ist teurer zu belassen als zu drehen.

**Zur Notiz über `QUIZ_RATE_LIMIT`: berechtigt, geschlossen.** Zwei Tests — der erste feuert einen Request mehr als erlaubt gegen dasselbe Konto und erwartet die 429 an der richtigen Stelle, der zweite zeigt, dass ein zweites Konto danach weiterhin 201 bekommt, also die Policy (`account_key`) und nicht nur die Existenz des Dekorators. Wichtig dabei: `account_key` liest den rohen Header und sieht `dependency_overrides` nie — ohne echtes Bearer-Token hätte der Test still per Adresse gezählt und die falsche Policy bestätigt.

**Zur „bis zu 5"-Abweichung:** richtig, gehört in die PR-Beschreibung, damit der Reviewer sie abnickt statt entdeckt.

**Zu den Dubletten:** Zustimmung, keine Änderung — mit einer Ergänzung: bei Temperatur 0 sind zwei Läufe auf *derselben* Stichprobe wortgleich, die Variation hängt allein an der zufälligen Chunk-Auswahl. In einem kleinen Bereich zieht die Stichprobe fast immer dasselbe, es sind also echte Dubletten. Als Punkt an T-35 notiert.

Danach: `ruff`, `mypy`, **431 Tests** (vorher 424) plus 6 E2E-Schema-Tests grün, Korrekturen in den einen Commit gesquasht.

---

## 6 — Nutzer

> bitte pushen und den PR erstellen

### Claude

Branch gepusht, [PR #97](https://github.com/tsorer/LearnFlow/pull/97) eröffnet, Titel mit dem Branchnamen präfixt (CLAUDE.md). Drei Punkte, die der Reviewer ausdrücklich abnicken soll, nach oben gezogen: die Abweichung „5 Fragen" → „bis zu 5", die Replace-Semantik und dass die Konfidenz-Pipeline hier bewusst nicht mitläuft. Dazu die beiden Mängel aus dem manuellen Durchlauf, die schärfere Fassung aus dem Review, und die bekannten Grenzen.

CI grün in allen drei Required Checks.

Zum Schluss auf einen Punkt hingewiesen, der ausserhalb des Auftrags lag: **In #42 und #43 sind die zugehörigen Stories vertauscht** — T-35 („Stefan Quiz-Review Dashboard") ist US-07, im Issue steht US-08; T-36 („Lara Quiz-UI") ist US-08, im Issue steht US-07.

---

## 7 — Nutzer

> ja, die Metadaten bei #42 und #43 nachziehen

### Claude

Jeweils nur die Zeile `Abhaengig von` geändert, der Rest der Bodies unverändert:

- **#42 (T-35):** `T-33, T-34` → `T-33 + T-34 (zusammen umgesetzt, #97)`
- **#43 (T-36):** `T-35` → `T-35 · Schema und Generierung liegen mit T-33 + T-34 vor (#97)`

Bei #43 blieb die Abhängigkeit auf T-35 stehen — die ändert sich durch die Zusammenlegung nicht. Ergänzt wurde nur der Hinweis, dass die Spalten, die T-36 braucht (`explanation`, `source_excerpt`, `chunk_id`), bereits aus diesem PR kommen.

Die vertauschten Stories wurden **nicht** angefasst, weil sie ausserhalb der Anweisung lagen; die Rückfrage dazu blieb offen.

---

## Offene Punkte

- **Vertauschte Stories in #42 / #43** — T-35 trägt US-08 statt US-07, T-36 trägt US-07 statt US-08. Beide zeigen auf die Story des jeweils anderen Tickets. Nicht korrigiert.
- **Ob eine Frage inhaltlich zu ihrer Passage passt, prüft nichts maschinell.** Das Eval-Gate aus ADR-009 misst den Antwortpfad, nicht diesen. Im ADR-Nachtrag festgehalten, samt Hebel für später (Self-Check über Frage und Passage).
- **Keine Deduplizierung** wiederholter Generierungsläufe — als Punkt an T-35 notiert.
- **`approved_at` wird angelegt, aber nicht geschrieben** — Freigeben / Ablehnen / Editieren gehört zu T-35 (#42).

---

## Nachtrag (Stand 2026-08-31)

PR #97 wurde am 2026-08-27 approved und als `66c06b3` nach `main` gemergt; #40 und #41 sind geschlossen. Die Metadaten-Zeile in #42 wurde seither von anderer Seite um einen Verweis auf #98 (T-49: Endpoints) erweitert — die hier gesetzte Angabe steht unverändert darin.
