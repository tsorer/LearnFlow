# Chatverlauf — T-19 Quellenreferenz-Validierung (Stufe 2 der Konfidenz-Pipeline)

**Datum:** 2026-08-20 bis 2026-08-25
**Branch:** `feat/T-19-quellenreferenz-validierung`, angelegt von `origin/main`. Der Arbeitsbaum wurde vom Nutzer während der Sitzung mehrfach nebenbei umgestellt (`feat/T-18-llm-generation`, `Frank`, `feat/T-15-document-versioning`, `main`); der T-19-Stand wurde in diesen Phasen über `git show <ref>:<pfad>` gelesen statt ausgecheckt.
**Gegenstand:** Issue [#26](https://github.com/tsorer/LearnFlow/issues/26) „[T-19] Quellenreferenz-Validierung" (Sprint 5, US-01) — Stufe 2 aus ADR-008: Grounding-/Citation-Check nach der Generierung.
**Ergebnis:** [PR #86](https://github.com/tsorer/LearnFlow/pull/86) mit vier Commits, dreimal auf `main` rebased, zwei Review-Runden von zwei Reviewern, [approved](https://github.com/tsorer/LearnFlow/pull/86) und mergebereit; CI grün (`backend`, `frontend`, `e2e`). Nebenprodukt: Issue [#90](https://github.com/tsorer/LearnFlow/issues/90) (T-46) zu lose typisierten Spec-Feldern.

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> Erstelle einen Umsetzungsplan für https://github.com/tsorer/LearnFlow/issues/26

### Claude

**Vorgehen:** Issue #26 gelesen; Abhängigkeit T-18 (#25) geprüft; ADR-008 vollständig; den bestehenden Query-Pfad (`app/routers/query.py`, `app/services/confidence.py`, `app/services/generation.py`, `app/services/config.py`), `openapi.yaml` und die Frontend-Anzeige (`MessageBubble.tsx`).

**Ausgangsbefund:** Stufe 2 war im Code bereits vorgezeichnet, aber leer — `citation_coverage` hart auf `0.0`, der Docstring von `confidence.py` verwies auf die fehlende Stufe, und `MessageBubble.tsx:261` suchte bereits nach einer Stage mit `id === "citation_coverage"`. Die Schwelle `min_citation_coverage` (Default 0.50) wurde gelesen, aber von niemandem ausgewertet.

**Blocker benannt:** T-18 lag nicht auf `main`, sondern offen als PR #84, mit uncommitteten Änderungen im Arbeitsbaum. Empfehlung, #84 zuerst zu mergen, statt T-19 auf dem T-18-Branch zu basieren.

**Plan in sechs Schritten:** Spec zuerst (neue `suppression_reason`-Werte), Prüflogik als pure Funktion in `confidence.py`, Verdrahtung in `query.py`, Debug-Stufe plus Frontend-Label, Tests, ADR-Nachtrag. Dazu die drei offenen Entwurfsentscheide (Segmentdefinition, Referenzformat-Toleranz, ein oder zwei Unterdrückungsgründe) mit Empfehlung, und der Vorbehalt, dass das Eval-Gate der DoD mangels Harness (T-27/T-28 offen) nicht mechanisch prüfbar ist.

**Rückfragen:** ein oder zwei Suppression-Reasons (Empfehlung: zwei), und ob #84 zuerst gemergt wird.

---

## 2 — Nutzer

> Schritt 1: ja, zwei Gründe verwenden. T-18 ist nun im main. Erstelle einen neuen Branch und starte mit der Umsetzung

### Claude

T-18 auf `main` verifiziert (inkl. der zuvor uncommitteten `MAX_RETRIES = 0`-Änderung), Branch von `origin/main` angelegt, dann der Plan der Reihe nach:

- **Spec:** `citation_coverage` und `citation_invalid` ins `suppression_reason`-Enum, Beschreibung von `ConfidenceInfo.citation_coverage` präzisiert („0.0 heisst auch: Stufe 2 lief nicht"), `schema.d.ts` via Container-Generator neu erzeugt.
- **`confidence.py`:** `check_citations(answer, citation_count) -> CitationDetail`, pur, ohne DB und LLM. Segment = Satz oder Listenpunkt, deutsche Abkürzungsliste, Referenz hinter dem Satzpunkt wird der Aussage davor zugerechnet, Fragmente unter vier Wörtern zählen nicht.
- **`query.py`:** Validität vor der Schwelle, `<` gegen `min_citation_coverage`; Stufe 2 läuft nur auf erzeugtem Text.
- **Zwei Funde über den Issue-Scope hinaus:** `answer_text` wäre bei Stufe-2-Unterdrückung erstmals mit echtem Text persistiert worden (Stufe 2 ist die erste Stufe, die vorhandenen Text zurückhält) — bleibt jetzt `NULL`. Und die Spalte `answers.citation_coverage` unterscheidet `NULL` (nicht gemessen) von `0.0` (gemessen, nichts belegt), während das API-Feld beide auf 0.0 zusammenfallen lässt.
- **Tests:** 26 Unit-, 12 Integrationstests. Eine eigene Erwartung erwies sich als falsch: eine erfundene Referenz belegt ihr Segment nicht — der Code hatte recht, der Test wurde korrigiert.
- **ADR-008** fortgeschrieben: Zwischenstand auf Stufen 0–2, Nachtrag mit den drei Festlegungen.

**Verifikation:** `ruff` + `mypy` + 242 Backend-Tests grün, Frontend `lint` + `tsc` + 49 Tests grün. Dazu live gegen den laufenden Stack (SKOS-Korpus, echte Modellantworten): belegte Antwort ausgeliefert (Coverage 0.6), dünn belegte unterdrückt, Refusal → Stufe 2 korrekt „nicht ausgeführt".

Nicht committet, sondern angeboten.

---

## 3 — Nutzer

> bewerte kritisch diese 3 Befunde:
> [drei Befunde zur Segmentierung: `_attach_trailing_references` über Zeilengrenzen, die Ein-Buchstaben-Abkürzungsregel, und numerische Klammern aus dem Quelltext; dazu zwei Nits zum `PipelineConfig`-Docstring und zum `MIN_SEGMENT_WORDS`-Kommentar]

### Claude

Alle drei am Interpreter reproduziert statt übernommen.

**Befund 1 — bestätigt, gefixt.** n=2 → 0.5, n=3 → 0.6667, n=4 → 0.75, exakt wie beschrieben. Ergänzend eingeordnet: das war ein Widerspruch im eigenen Entwurf — `_segments` splittet bewusst zuerst nach Zeilen, weil der Umbruch eine Segmentgrenze ist, und dann griff die Reparatur über genau diese Grenze. Verschoben nach `_sentences`, wirkt jetzt pro Zeile.

**Befund 2 — bestätigt, gefixt, der schwerere.** „Anhang A." wurde als Abkürzung gelesen, die unbelegte Aussage vom Folgesatz mitgetragen: 1.0 statt 0.5, fail-open. Neue Regel: einzelner Kleinbuchstabe gilt immer, einzelner Grossbuchstabe nur als zweite Hälfte eines Paars (`_LETTER_PAIR_ABBREVIATION`) — „z. B." und „i. S. v." halten, „Anhang A." splittet.

**Befund 3 — mechanisch korrekt, aber als Defekt zurückgewiesen.** Die offene Bedingung des Befunds („hängt daran, ob der Korpus eckige Zahlenklammern führt") wurde gemessen: 0 Treffer im EU AI Act (706.553 Zeichen), 0 im SAMW-Leitfaden (238.905 Zeichen), 0 in den 206 geseedeten Chunks. Dazu zwei inhaltliche Einwände: die Fehlerrichtung ist Unterdrückung, die ADR-008 ausdrücklich als akzeptablen Fehler führt, und jede Entschärfung entschuldigt genau die erfundene Referenz, für die Stufe 2 existiert. Als bekannte Grenze im ADR festgehalten statt Code geändert.

**Beide Nits berechtigt und korrigiert.** Beim zweiten bewusst nur der Kommentar präzisiert, keine Sperre: `min_citation_coverage = 0.0` schaltet die Coverage-Prüfung ab, genau wie `similarity_threshold = 0.0` Stufe 0 abschaltet — ein Betreiber, der eine Stufe deaktiviert, und eine Zusatzbedingung stünde in keinem ADR.

245 Tests grün; live nachgefahren, die dünn belegte Antwort steht durch die geänderte Segmentierung jetzt bei 0.4 statt 0.3333, das Ergebnis (Unterdrückung) unverändert.

---

## 4 — Nutzer

> ja, alles committen und dann den pr erstellen

### Claude

Vor dem Commit geprüft, dass der Index den Arbeitsbaum vollständig deckt und nichts Untracked mitläuft (zwei Dateien waren vom Nutzer nebenbei gestaged worden). Commit, Push, PR #86 erstellt; CI-Wartelauf im Hintergrund gestartet.

---

## 5 — Nutzer

> ich sage dir, wenn du pushen bzw. den pr erstellen sollst. Die Notiz „Nutzer pusht und öffnet PRs selbst" kannst du also anpassen

### Claude

Memory-Notiz umgeschrieben: Push und PR-Erstellung macht Claude, aber nur auf ausdrückliche Ansage — nie unaufgefordert. Mit aufgenommen: der ursprüngliche Wortlaut zur Nachvollziehbarkeit, und die in dieser Sitzung aufgetretene Push-Falle — ein Branch aus `git checkout -b <name> origin/main` trackt `origin/main`, ein blosses `git push` liefe auf `main`, daher immer `git push -u origin <branchname>`.

---

## 6 — Nutzer

> schau dir das Feedback auf GIT an und hinterfrage die Punkte kritisch

### Claude

Review von `tsorer` gelesen (drei Punkte), alle Zeilennummern verifiziert.

**Punkt 1 (Satzgrenzen-Logik mit `chunking.py` konsolidieren) — Hauptvorschlag abgelehnt, messbar.** Den Splitter aus `chunking.py` isoliert nachgebaut und beide auf dieselben Fälle laufen lassen: „Anhang **B**." und „Anhang **S**." splittet `chunking` nicht, weil seine Liste `"B"` und `"S"` case-sensitiv führt — auf Antworttext angewandt genau der fail-open-Bug aus Befund 2, eine Runde zuvor gefixt. Und `chunking.py:49` rangiert Sätze ausdrücklich **über** Zeilenumbrüchen, weil ein Umbruch im PDF-Textlayer ein Layout-Artefakt ist — für generierten Markdown das Gegenteil, das war Befund 1. Die beiden sind gegensätzlich ausgelegt, weil sie gegensätzliche Eingaben lesen.

**Der Nebenpunkt traf dafür härter als formuliert.** Fehlt Stufe 2 eine Abkürzung, entsteht ein falscher Split und ein unbelegtes Zusatzsegment: `etc.`, `Bst.`, `Abb.` drückten eine korrekt belegte Ein-Satz-Antwort von 1.0 auf 0.5. `etc` ist im Pilotkorpus ausgezählt. Übernommen.

**Punkt 2 (doppelter Schwellenwert-Vergleich) — zugestimmt, und geschärft:** Stufe 2 brach ein Muster, das dieselbe Funktion für Stufe 0 und 1 bereits einhält (`gate_passed`, `confidence_passed` einmal im Handler berechnet und durchgereicht).

**Punkt 3 (`hasCitationStage`-Hoist) — korrekt, aber als Fremdcode aus T-18 eingeordnet.**

Wegen der uncommitteten T-15-Arbeit des Nutzers im Arbeitsbaum nicht implementiert, sondern Vorgehen vorgeschlagen.

---

## 7 — Nutzer

> die Arbeiten an T-15 sind abgeschlossen. Du kannst den Branch wechseln. Mach bitte auch gleich noch ein Rebase auf den main und setze dann die Anpassungen wie vorgeschlagen um (eigener Commit und kein Squash)

### Claude

Arbeitsbaum als sauber verifiziert, gewechselt, konfliktfrei auf `main` rebased. Dann die drei Punkte: Abkürzungsliste um `etc`, `bst`, `buchst`, `abb`, `tab` ergänzt mit Begründungskommentar zur bewussten Trennung von `chunking.py`; `citation_passed` einmal im Handler; Hoist im Frontend. Als eigener Commit.

---

## 8 — Nutzer

> ja, force-push und den Kommentar an den PR

### Claude

Vor dem Überschreiben mit `git range-diff` verifiziert, dass der rebasete Commit inhaltsgleich zum überschriebenen ist (`=`); `--force-with-lease`. PR-Kommentar mit der Messtabelle als Begründung für die Absage an die Konsolidierung.

---

## 9 — Nutzer

> sollte "citation_coverage" nicht besser als Konstante definiert werden?

### Claude

Nach Fundstelle unterschieden statt pauschal bejaht.

- **Backend-Produktivcode:** bereits Konstanten (`REASON_CITATION_COVERAGE`, `STAGE_CITATION_COVERAGE`). Dass zwei Konstanten denselben Wert tragen, ist Absicht — die Stufe ist eine, sie unterdrückt aus zwei Gründen; ein Zusammenziehen benennte beim Umbenennen der Stage-ID lautlos einen Spec-Enum-Wert mit um.
- **Tests:** Literale sind hier die **stärkere** Variante — ein Test gegen die Konstante bliebe grün, wenn deren Wert falsch wird.
- **Frontend:** die echte Lücke. Der Label-Key ist über `Record<SuppressionReason, string>` typgeprüft, die Stage-ID nicht, weil `StageInfo.id` in der Spec nur `type: string` ist — zweimal dasselbe Literal, Tippfehler kompiliert durch.
- **Und ein Loch, das keine Konstante schliesst:** nichts prüfte, ob die `REASON_*`-Werte dem Spec-Enum entsprechen.

Gegen ein Enum für `StageInfo.id` argumentiert, weil `DebugInfo` in der Spec ausdrücklich als „Nicht Teil des fachlichen Vertrags" deklariert ist.

---

## 10 — Nutzer

> zeig mir die Stelle in der Spec zu DebugInfo, von dem kommt die Info?
> OK, setze die beiden Punkte um und erstelle ein neues Issue, dass geprüft werden soll, ob DebugInfo (und eventuell auch andere Variablen?) als Enum definiert werden sollte und das es in einem ADR dokumentiert werden sollte.

### Claude

Fundstelle gezeigt (`openapi.yaml`, Schema-Beschreibung von `DebugInfo`), Herkunft auf #76 (T-39) zurückverfolgt.

**Umgesetzt** in `6b4f405`: `CITATION_STAGE_ID` im Frontend, und `test_suppression_reasons_match_the_spec_enum` in beide Richtungen — die Konstanten werden per Präfix eingesammelt, damit T-25s Reason ohne Zutun mit abgedeckt ist. Wirksamkeit per Mutation belegt: eingeschleustes `"citation_coverag"` lässt den Test fallen.

**Issue [#90](https://github.com/tsorer/LearnFlow/issues/90) (T-46)** erstellt. Beim Recherchieren zeigte sich, dass die Drift nicht hypothetisch ist: `DebugInfo.params_used` hat freie Keys, und drei von fünf gesendeten Parametern (`retrieval_top_k`, `context_top_n`, `rrf_k`) haben im Frontend kein Label und werden dem Admin als Rohschlüssel angezeigt, während sechs Labels für nie gesendete Keys vorgehalten werden. Das steht als Beleg im Issue.

---

## 11 — Nutzer

> push

### Claude

Regulärer Push (kein Force, da nur ein Commit obendrauf). CI-Wartelauf gestartet.

*Anmerkung: Ein erster Wartelauf meldete fälschlich Erfolg — die Abbruchbedingung suchte leere Conclusions nur am Zeilenende, `backend` und `e2e` standen in der Mitte. Der Fehler wurde bemerkt, die Meldung korrigiert und die Schleife auf `status == COMPLETED` umgestellt. Seither wird jedes CI-Ergebnis zusätzlich per direkter Abfrage gegengeprüft.*

---

## 12 — Nutzer

> schau dir die neuen Kommentare an. Was genau mach die Fabrikations-Prüfung? Was soll das Problem mit [2026] sein? Die Quellen müssen wir doch selber referenzieren? Es geht doch darum, wo innerhalb vom hochgeladenen Material die Antwort belegt werden kann?

### Claude

Zweites Review (`luenlestra`) gelesen: kein Approve, weil AK 2 an einem Loch hängt — `_REFERENCE` war auf `\d{1,3}` begrenzt, eine vierstellige Klammer damit für die Prüfung unsichtbar.

Am Interpreter reproduziert. Der Kern in einer Zeile: dieselbe Aussage mit `[12]` wurde unterdrückt, mit `[2026]` ausgeliefert.

**Die Rückfrage des Nutzers traf den Kern besser als das Review.** `n` ist unser Positionsindex in die Kontextliste, die der Prompt dem Modell übergibt — 1 bis `context_top_n`, im Default fünf; keine Dokumentnummern, keine Jahreszahlen. Damit kann `[2026]` unter keiner Lesart eine gültige Referenz sein, und die vom Review vermutete Absicht („`[2026]` ist plausibel") trägt nicht: für genau diese Mehrdeutigkeit steht die Entscheidung bereits im ADR, im Absatz zur zitierten `[12]`. Der Code widersprach seiner eigenen dokumentierten Festlegung — er lockerte bei vier Ziffern still, was er bei zwei streng behandelte. Damit sind die zwei Optionen des Reviews nicht gleichwertig.

---

## 13 — Nutzer

> ja, bitte umsetzen. Durch die Nacharbeiten an T-15 musst du nochmal ein rebase auf den main machen

### Claude

Rebase auf `main` (inzwischen T-15/#87, T-20/#85, T-31/#88, T-37/#89), zwei Konflikte:

- `Docs/04_ADR-008_...` — rein additiv, `main` hatte den T-37-Nachtrag bekommen. Beide behalten, chronologisch einsortiert.
- `tests/test_openapi_spec.py` — Import-Konflikt. Nebenbefund: `main` hatte über T-15 unabhängig denselben Konformitätstest-Ansatz eingeführt (`test_document_status_enum_matches_the_model`).

Dann `\d{1,3}` → `\d+`, die Bereichsprüfung entscheidet. Nebeneffekt: `[1, 2345]` matchte vorher gar nichts und nahm die legitime `1` mit. Zwei Unit-Tests, ein Integrationstest mit dem Beispielsatz des Reviews, Festlegung im ADR-Nachtrag Punkt 2 samt Preis (eine Jahreszahl in eckigen Klammern unterdrückt jetzt).

**Die Merge-Warnung des Reviews abgeprüft:** `MessageBubble.tsx` merged konfliktfrei, obwohl `main` sie zweimal bewegt hatte — voller Frontend-Gate statt nur Push, 81 Tests grün. Backend 293 grün.

---

## 14 — Nutzer

> ja, force-push und im PR antworten

### Claude

`range-diff` vor dem Überschreiben: genau die zwei Commits mit Konfliktauflösung als geändert markiert, der dritte `=`, der vierte neu. Push mit `--force-with-lease`, dann die Antwort im PR — inhaltlich getragen von der Rückfrage aus Turn 12.

---

## 15 — Nutzer

> T-45 wurde zuerst gemergt. PR wurde approved. Bitte ein Rebase machen und nochmal pushen

### Claude

Rebase auf `main` mit T-45 (#91) — **konfliktfrei**, und genau davor hatte das Review gewarnt (bei #85 merged `ChatView.tsx` sauber und kompilierte trotzdem nicht). Deshalb nicht auf den sauberen Merge verlassen:

- `range-diff`: nur ein geänderter Commit, darin genau eine Zeile — `question=request.question` → `question=body.question`, T-45s Umbenennung auf einer Zeile, die der Commit anfasst. Keine inhaltliche Änderung.
- Voller Quality Gate: Backend 299 Tests, Frontend 82 Tests, beide grün. Das Rate-Limit aus T-45 bricht die Query-Tests nicht; `check-api-types` bestätigt, dass `schema.d.ts` zur gemergten `openapi.yaml` passt und die neuen Enum-Werte den Rebase überstanden haben.

Force-Push. CI grün auf allen drei Jobs, `reviewDecision: APPROVED`, `MERGEABLE`.

---

## 16 — Nutzer

> du kannst in der Zwischenzeit schon den Chatverlauf nach Frank/Prompts exportieren

### Claude

Dieser Export.

---

## Ergebnis

**Vier Commits auf `feat/T-19-quellenreferenz-validierung`** (Hashes nach dem letzten Rebase):

| Commit | Inhalt |
|---|---|
| `b39fa89` | citation check as stage 2 |
| `6bdfb75` | address review on PR #86 |
| `6b4f405` | pin the citation_coverage wire value |
| `36a05b8` | validate references of any digit count |

**Die drei Akzeptanzkriterien aus #26:**

| AK | Erfüllt durch |
|---|---|
| Jede Antwort enthält mindestens eine Quellenreferenz | Kein `[n]` → Coverage 0.0 < Schwelle → unterdrückt |
| Nicht validierbare Quellenreferenz → unterdrückt | Index ausserhalb `1..n` → `valid = False`, unabhängig von der Coverage |
| Unterdrückte Antwort → definierter Fallback-Text | `MESSAGE_CITATION_*`, standardisiert; `answer_text` wird nicht persistiert |

**Offen aus der Definition of Done:** Das Eval-Gate ist mangels Harness nicht mechanisch prüfbar (T-27/T-28 offen) — im PR als Vorbehalt vermerkt.

**Was über den Issue-Scope hinaus entstand:**

- `answer_text` bleibt bei Unterdrückung `NULL` — Stufe 2 ist die erste Stufe, die vorhandenen Text zurückhält; ein gespeicherter Entwurf hätte in der Auswertung als ausgelieferte Antwort gezählt (ADR-009).
- `answers.citation_coverage` unterscheidet `NULL` von `0.0`.
- Konformitätstest `test_suppression_reasons_match_the_spec_enum`, per Mutation als wirksam belegt.
- Issue [#90](https://github.com/tsorer/LearnFlow/issues/90) (T-46) zu lose typisierten Spec-Feldern, mit der bereits eingetretenen `params_used`-Drift als Beleg.
- ADR-008: Nachtrag „Wie Stufe 2 misst" mit den Festlegungen zu Segmentdefinition, Referenzformat und den zwei Unterdrückungsgründen, plus zwei bekannten Grenzen.

**Aus den Reviews behoben — beide Male in der fail-open-Richtung:**

| Fund | Wirkung vorher |
|---|---|
| Referenz-Reparatur über Zeilengrenzen | Zwei belegte Aufzählungspunkte → Coverage 0.5 statt 1.0 |
| „Anhang A." als Abkürzung gelesen | Unbelegte Aussage vom Folgesatz mitgetragen, 1.0 statt 0.5 |
| `\d{1,3}` in `_REFERENCE` | `[2026]` unsichtbar → Antwort mit erfundener Quelle ausgeliefert |

**Zweimal gegen einen Review-Vorschlag entschieden, mit Messung statt Meinung:** die Konsolidierung der Satzgrenzen-Logik mit `chunking.py` (hätte beide Segmentierungs-Bugs zurückgeholt) und die Einstufung der zitierten `[12]` als Defekt (0 Treffer in 945.000 Zeichen Korpus; Fehlerrichtung ist Unterdrückung, die ADR-008 als akzeptabel führt).
