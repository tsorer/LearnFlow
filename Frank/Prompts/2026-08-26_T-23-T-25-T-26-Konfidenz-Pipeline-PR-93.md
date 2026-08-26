# Chatverlauf — T-23 / T-25 / T-26 Komposit-Konfidenz, Self-Check und Unterdrückungsreihenfolge

**Datum:** 2026-08-22 bis 2026-08-26
**Branch:** `feat/T-23-T-25-T-26-konfidenz-pipeline`, angelegt vom noch offenen T-19-Stand (`31354a4`). Nachdem T-19 gesquasht in `main` gelandet war (`28d09b4`, PR #86), mit `git rebase --onto origin/main 31354a4` auf `main` umgesetzt — fünf Konflikte.
**Gegenstand:** [#30](https://github.com/tsorer/LearnFlow/issues/30) „[T-23] Konfidenz-Score-Berechnung", [#32](https://github.com/tsorer/LearnFlow/issues/32) „[T-25] Self-Check-Pipeline: LLM-Selbstevaluation", [#33](https://github.com/tsorer/LearnFlow/issues/33) „[T-26] Unterdrueckungslogik einbinden" (Sprint 5, US-02) — die Stufen 2b und 3 aus ADR-008 sowie deren Reihenfolge.
**Ergebnis:** [PR #93](https://github.com/tsorer/LearnFlow/pull/93) mit zwei Commits, approved, CI grün (`backend`, `frontend`, `e2e`). Nebenprodukte: Issues [#95](https://github.com/tsorer/LearnFlow/issues/95) (T-47) und [#96](https://github.com/tsorer/LearnFlow/issues/96) (T-48) zum Gold-Eval-Dataset; lokale Korrektur der `Src`/`src`-Schreibweise.

> Nutzer-Prompts wörtlich aus dem Sitzungstranskript. Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> Erstelle einen Umsetzungplan für T-23, T-25 und T-26. Alle drei sollen zusammen umgesetzt werden. Verwende als Grundlage T-19, auch wenn dieser PR noch nicht gemergt ist.

### Claude

**Erste Hürde: die Nummerierung.** `gh issue view 23` liefert nicht T-23, sondern „[T-16] React: Upload-UI" — GitHub-Issue-Nummern und T-Nummern stimmen in diesem Repo nicht überein. Über die Titel gesucht und die richtigen gefunden: [#30](https://github.com/tsorer/LearnFlow/issues/30) (T-23), [#32](https://github.com/tsorer/LearnFlow/issues/32) (T-25), [#33](https://github.com/tsorer/LearnFlow/issues/33) (T-26), Basis [#26](https://github.com/tsorer/LearnFlow/issues/26) (T-19).

**Aus den Issue-Kommentaren:** Die gemeinsame Umsetzung war dort bereits als offene Frage notiert (Backlog-Durchsicht 2026-08-16) — T-23 ändert allein kein Verhalten, T-26s Reihenfolge ist ohne den Score nicht abnehmbar. Gegenargument in derselben Notiz: die Gewichte sind unkalibrierte Hypothesen.

**Gelesen:** ADR-008 vollständig, `app/routers/query.py`, `app/services/confidence.py`, `app/services/config.py`, dazu der T-19-Commit `31354a4`.

Ein ausformulierter Plan kam nicht mehr zustande — die Freigabe traf ein, während die Analyse noch lief.

---

## 2 — Nutzer

> Ja, branch anlegen und dann alle Punkte umsetzen

### Claude

Branch `feat/T-23-T-25-T-26-konfidenz-pipeline` vom T-19-Stand (`31354a4`) angelegt, dann der Reihe nach:

- **Spec zuerst** (ADR-010): `suppression_reason` um `confidence_band` und `self_check` erweitert, `ConfidenceInfo` um `band` (`hoch`/`mittel`/`niedrig`), `score`-Beschreibung auf das Komposit umgestellt.
- **`confidence.py`:** `compute_composite()` und `band_for()` als pure Funktionen, dazu `in_self_check_band()`. Gewichte je 0.5 als benannte Konstanten **im Code**, nicht in `config` — eine Gewichtsänderung verschiebt die Skala, auf der jeder gespeicherte `confidence_score` sitzt, und das ist die Kalibrierungsgrundlage aus ADR-009. ADR-008 sagte an dieser Stelle „Gewichte in `config`"; der Widerspruch wurde als Korrektur ins ADR geschrieben statt still anders umgesetzt.
- **`self_check.py`** neu, weil Stufe 3 die einzige nicht-deterministische Stufe ist. Verifikations-Prompt mit sechs Regeln, Sentinel-Kontrakt `GEDECKT` / `NICHT_GEDECKT`, `read_verdict()` getrennt vom Provider-Aufruf, damit die Fail-closed-Regel ohne Provider testbar ist. Der Kontext wird über das gemeinsame `render_context()` aus `generation.py` gerendert, damit der Prüfer dieselbe Nummerierung sieht wie der Autor.
- **`query.py`:** Stufen in der Reihenfolge aus dem US-02-Entscheid vom 2026-05-20 — Citation → Komposit-Band → Self-Check. Dazu `REFINEMENT_HINTS` je Grund (Requirements §71), statisch abgeleitet: einen Provider ausgerechnet auf dem Pfad zu befragen, der existiert, weil die Pipeline einem Modell nicht getraut hat, wäre der falsche Ort.
- **Migrationen:** Grenzband seeden plus aufgeschobener `CONSTRAINT TRIGGER` für `low <= high`; `answers.self_check_passed` als nullable Spalte.
- **Docs:** ADR-008-Nachtrag, Requirements US-02, ERD, Pilotstart-Checkliste.

Die Sitzung wurde durch den Ruhezustand des Rechners unterbrochen.

---

## 3 — Nutzer

> Mein Computer ist in den Ruhezustand gewechselt, während du gearbeitet hast. Bitte mach dort weiter, wo du aufgehört hast.

### Claude

**Zuerst den Ist-Zustand geprüft, nicht angenommen** — Docker war wieder oben, die Container liefen.

- Tests fertiggestellt: `tests/test_self_check.py` neu, `test_query.py` um Stufe 2b/3, Persistenz und Hinweise erweitert, `test_services_config.py` um das Grenzband, dazu ein e2e-Test gegen die echten DB-Constraints.
- **`make qa`-Äquivalent:** Backend 338 Tests, `ruff`, `mypy` — ein mypy-Fund: die Band-Konstanten weiteten sich zu `str`, Literal-Annotation nachgezogen. Frontend 49 Tests grün; die lokalen Fehlschläge vorher waren Node 24, nicht der Code.
- **Alembic-Drift:** Die Dev-DB war auf die neue Revision gestempelt, ohne dass die Grenzband-Migration gewirkt hatte (Container-Start mitten im Schreiben der Datei). Downgrade und erneuter Upgrade brachten alles korrekt — und prüften den Downgrade-Pfad gleich mit.
- **Manueller Durchlauf gegen den echten Provider:** Die ersten Fragen zum EU AI Act endeten bei `generation_refused` — der geseedete Korpus besteht fast vollständig aus den SKOS-Richtlinien. Mit SKOS-Fragen feuerten alle fünf Stufen: Komposit `0.5*0.6899 + 0.5*0.5 = 0.5949`, Band «mittel», Self-Check ausgelöst und bestanden, zwei LLM-Aufrufe.
- **Fund aus dem Live-Lauf, nicht aus den Tests:** Die Self-Check-Zeile im Admin-View meldete „Score 0.5701 liegt ausserhalb des Grenzbands 0.5–0.75" — bei einem Score mitten darin. Übersprungen wurde die Stufe, weil vorher unterdrückt worden war; der Text kannte nur den Band-Grund. Behoben über einen `reached`-Parameter, mit Regressionstest.

Committet, nicht gepusht.

---

## 4 — Nutzer

> unter anderen T-19 ist nun im main. Mach bitte ein rebase

### Claude

**Befund vor dem Rebase:** T-19 war **gesquasht** gemergt (`28d09b4`, PR #86) — der lokale Basis-Commit `31354a4` ist damit kein Vorfahre von `origin/main`. Ein `git rebase origin/main` hätte beide Commits erneut abgespielt. Zusätzlich enthielt `main` inzwischen T-15, T-20, T-31, T-37 und T-45, und die gesquashte T-19-Version trug die Review-Nacharbeit aus #86, die der lokalen Basis fehlte.

Backup-Branch angelegt, dann `git rebase --onto origin/main 31354a4` — nur der eigene Commit. Fünf Konflikte: ADR-008 (beide Seiten additiv, beide Nachträge behalten), `query.py`, `test_confidence.py`, `test_query.py`, `MessageBubble.tsx`.

Beim Nachziehen der Migrationsdateien schlug `git mv` fehl: das Quellverzeichnis heisst auf der Platte `Src`, git trackt `src`.

---

## 5 — Nutzer

> kann lokal einfach 'Src' in 'src' umbenannt werden, um die Probleme zu vermeiden?

### Claude

Geprüft statt geschätzt:

| | |
|---|---|
| Auf der Platte | `Src/` |
| Im Git-Index | 129 Dateien unter `src/`, **null** unter `Src/` |
| Je als `Src/` committet | nie |
| `core.ignorecase` | `true` |
| Betroffen | nur die oberste Ebene |
| Referenzen in Configs | keine — CI-Workflow nutzt `src/` |

**Antwort: ja**, reine Dateisystem-Korrektur, git sieht danach keine Änderung, CI war nie betroffen (frischer Klon zieht `src` aus dem Index). Ursache der Falle benannt: `core.ignorecase` löst *getrackte* Pfade über den Index auf, der Pfad einer **neuen** Datei kommt aber vom Dateisystem — deshalb verfehlt `git add src/neu.py` neue Dateien lautlos.

Zwei Bedingungen genannt: NTFS ist case-insensitiv (`mv Src src` wäre ein No-op, es braucht einen Zwischennamen), und die Container binden `...\Src\backend` ein, müssen also unten sein. Dazu die Entwarnung: Compose-Projektname ist ohnehin `src`, und die DB liegt im benannten Volume `learnflow_pgdata`, überlebt also ein `down`.

---

## 6 — Nutzer

> docker hab ich gestoppt. Bitte ausführen

### Claude

- Verifiziert, dass der Daemon wirklich aus war, dann `mv Src src_tmp && mv src_tmp src`.
- **Git sieht keine Änderung** — wie vorhergesagt.
- **Falle verifiziert weg:** Eine neue Datei unter `src/backend/` angelegt, mit `git add src/...` gestaged — sie landet jetzt im Index. Probe wieder entfernt.
- Docker Desktop gestartet, Stack hoch. Bind-Mount zeigt auf `...\LearnFlow\src\backend`, Container-Namen unverändert, DB unangetastet auf Revision `0015` mit allen 206 Chunks.
- Kontrolllauf: Backend 361 + `ruff` + `mypy`, e2e 39, Frontend 82 — alles grün.
- Memory-Eintrag umgeschrieben: der bisherige Workaround `git add Src/...` ist ab jetzt der **falsche** Weg.

---

## 7 — Nutzer

> bitte vor Umsetzung kritisch prüfen:
>
> Befunde
> 1. Fail-open im Verdict-Parser — self_check.py:196
> upper.startswith(VERDICT_COVERED) lässt beliebigen Nachtext durch. Verifiziert im Container:
> 'GEDECKT - allerdings steht Artikel 9 nicht im Kontext.' -> passed = True
> 'Gedeckt, bis auf die Frist von 24 Monaten.'             -> passed = True
> Genau die relativierende Formulierung, die ein Modell statt Regel 5 produziert, passiert das Gate. Das ist die Fehlerrichtung, die ADR-008 für die unlesbare Antwort ausschliesst — hier steht sie über der Prefix-Prüfung offen, und auf der Ablehnungsseite ist sie schon zu ("NICHT GEDECKT: …" mit Leerzeichen wird korrekt als unlesbar unterdrückt). Die Asymmetrie ist die eigentliche Schwäche.
> Minimaler Fix: nach dem Prefix verlangen, dass der Rest nur noch Satzzeichen/Leerraum ist. Bestehende Tests bleiben grün — "Gedeckt." und "GEDECKT" erfüllen das, test_the_raw_reply_is_kept_for_the_admin_view behauptet nichts über passed.
> 2. Lücke zwischen confidence_threshold_medium und self_check_band_low — 0014_self_check_band.py
> Aus der laufenden DB: medium = 0.45, self_check_band_low = 0.50. Daraus folgt:
> Score	Verhalten
> < 0.45	unterdrückt (confidence_band)
> 0.45 – 0.50	ausgeliefert, ohne Self-Check
> 0.50 – 0.75	Self-Check läuft
> ≥ 0.75	ausgeliefert, ohne Self-Check
> Die schwächsten ausgelieferten Antworten überspringen Stufe 3. Der Kommentar in 0014 begründet die Startwerte damit, das Band sei „auf die Mittel-Spanne zentriert, damit genau die Antworten mit zweifelhafter Bandzuordnung den Zusatzaufruf zahlen" — das trifft mit 0.45/0.50 nicht zu. Entweder self_check_band_low auf 0.45 seeden oder den Kommentar korrigieren und die Lücke als bewusst deklarieren.
> Verwandt: nichts verknüpft das Grenzband mit den Konfidenz-Bändern. self_check_band_high < confidence_threshold_medium schaltet Stufe 3 vollständig ab, ohne dass ein Constraint greift — dieselbe „unbemerkt abgeschaltet"-Falle, die trg_config_self_check_band_order für low > high schliesst, nur über einen anderen Weg. Sichtbar nur pro Anfrage im Admin-Debug.
> 3. Kommentar verweist auf ein Badge, das es nicht gibt — MessageBubble.tsx:509
> „The learner-facing display of US-02 is the band badge above" — oberhalb steht Composite, Retrieval, Citation, kein Band-Badge. confidence.band wird nur im DebugPanel (Zeile 319) gerendert. Der Kommentar beschreibt T-27, nicht den Ist-Zustand.
> 4. Zahlendreher im ADR — Docs/04_ADR-008, Nachtrag 2026-08-22, Punkt 2
> „dort sind 80 % und 50 % kalibrierbare Zahlen statt Selbstauskünfte" — die Startwerte sind 0.75 / 0.45. Docs/02_Requirements.md nennt sie korrekt. Ein Satz im ADR angleichen.
> 5. Spec-Formulierung ungenau — openapi.yaml, ConfidenceInfo.band
> „Bei einer vor der Generierung unterdrückten Antwort beschreibt das Band die Retrieval-Konfidenz" — gilt genauso für generation_refused und generation_truncated, also nach der Generierung. Die score-Beschreibung daneben formuliert es richtig („Lief Stufe 2 nicht, …").
> Was gut trägt
> Reihenfolge und Persistenz sauber getrennt: answer_text bleibt bei jeder Unterdrückung NULL (reason is None, nicht nur generation), citation_coverage und self_check_passed unterscheiden NULL („nicht gelaufen") von 0.0/false („gemessen/gescheitert"). Beides getestet.
> Ausfall ≠ Urteil konsequent durchgezogen: _self_check gibt 503, read_verdict unterdrückt — inklusive der (TypeError, AttributeError, NameError, ImportError)-Ausnahme, damit ein Bug kein 503 wird.
> render_context geteilt statt zweimal geschrieben — der Prüfer sieht dieselbe Nummerierung wie der Autor. Wichtiger Punkt, richtig gelöst.
> DebugInfo ohne Doppelberechnung: citation_passed wird einmal ermittelt und weitergereicht, band_passed unterscheidet „übersprungen weil klar" von „übersprungen weil nichts mehr da". _self_check_detail_texts reached-Parameter ist genau die Falle, die man sonst übersieht.
> Frontend: die erfundenen ?? 0.50 / ?? 0.75-Fallbacks sind raus, die Stufen-Nummerierung hängt nicht mehr an Indizes.
> Testabdeckung ist dicht (64 neue Tests inkl. e2e gegen die echten Constraints), ADR/Requirements/ERD/Pilotcheckliste alle mitgezogen.
> Empfehlung: Befund 1 vor dem PR fixen (kleiner, testbarer Eingriff, trifft das Kernversprechen). 2–5 sind Kommentar-/Doc-Korrekturen; Befund 2 braucht eine Entscheidung von dir — Startwert angleichen oder Lücke dokumentieren. Zusätzlich: Kommentar an Issue #30 zur AC-Abweichung und Vermerk im PR, dass US-02s Lernenden-Anzeige in T-27 bleibt.

### Claude

**Alle fünf Befunde selbst reproduziert, alle fünf bestätigt.**

**Befund 1 reicht weiter als beschrieben.** Statt die zwei genannten Beispiele nachzustellen, eine eigene Fallliste durch den Parser geschickt — und einen dritten Fall gefunden:

```
passed=True  <- 'Gedecktheit ist nicht gegeben.'
```

Eine glatte **Ablehnung, die als Bestätigung durchging**, weil `"GEDECKTHEIT"` mit `"GEDECKT"` beginnt. Es fehlte nicht nur die Nachtext-Prüfung, sondern die Wortgrenze. Fix: `_COVERED_ONLY` verlangt das Sentinel plus höchstens Satzzeichen. Der Einschätzung zur Asymmetrie wurde **widersprochen**: sie ist nicht die Schwäche, sondern folgt dem Prompt-Kontrakt — Regel 4 verlangt das Sentinel „ohne Begründung", Regel 5 verlangt Text danach; beide Zweige gleich streng zu machen würde jede wohlgeformte Ablehnung verwerfen.

**Befund 2** per Rückfrage entschieden (Grenzband auf `medium` angleichen vs. Lücke dokumentieren; Kopplung per Constraint vs. nur dokumentieren). Ergebnis: `self_check_band_low` auf 0.45, Angleichung per Unit- **und** e2e-Test festgenagelt, Kopplung als bekannte Grenze ins ADR.

**Dabei ein Fund, der im Review nicht stand:** Beim Neu-Anwenden der geänderten Migration starb der Downgrade-Pfad mit `ObjectInUseError` — die `DELETE` stellt aufgeschobene Events des Band-Triggers aus `0009` in die Warteschlange, und PostgreSQL verweigert ein `ALTER` bei anstehenden Events. `SET CONSTRAINTS ALL IMMEDIATE` vor dem `ALTER`; Downgrade und Re-Upgrade laufen beide.

**Befunde 3–5** als Kommentar- und Doku-Korrekturen umgesetzt; die Spec-Änderung zog eine Neugenerierung von `schema.d.ts` nach sich, die `npm run check` prompt einforderte.

Kontrolllauf: Backend 375, e2e 40, Frontend 82 — grün.

---

## 8 — Nutzer

> erstelle den Kommentar, mach einen Squash und erstelle dann den PR

### Claude

- **Squash:** `git reset --soft origin/main` plus Commit. Baum-Hash vor und nach identisch (`e33f511`) — inhaltlich nichts verschoben.
- **Push** und [PR #93](https://github.com/tsorer/LearnFlow/pull/93) erstellt, Titel mit Branchnamen prefixt, Vorbehalte (T-27, T-28, T-22, entkoppelte Bänder) im Text ausgewiesen.
- **Kommentare an [#30](https://github.com/tsorer/LearnFlow/issues/30) und [#32](https://github.com/tsorer/LearnFlow/issues/32)** — bewusst zwei statt des einen empfohlenen: beide Issues haben Akzeptanzkriterien, die nicht wie geschrieben umgesetzt sind, und die Abweichung bei T-25 ist die grössere. Wer #32 abnimmt, fände die AC sonst unerfüllt und ohne Erklärung vor.
- CI: `backend`, `e2e`, `frontend` alle grün.

---

## 9 — Nutzer

> Mach einen Vorschlag, was wir auf die zwei Punkte vom Feedback antworten können (siehe https://github.com/tsorer/LearnFlow/pull/93 Kommentar)

### Claude

Das Feedback zuerst gelesen statt geraten: Review von `luenlestra`, **approved**, kein Korrektheitsdefekt, drei niedrig-schwere Beobachtungen (Punkt 3 nennt der Reviewer selbst „gleiche Wurzel wie 1").

Beide Behauptungen nachgeprüft und bestätigt: `self_check_band_low` steht in `WRITABLE_KEYS`, ist also per Admin-PUT frei setzbar, ohne Cross-Field-Constraint; und die beiden Reader werden ausschliesslich in `query.py` direkt hintereinander aufgerufen, `admin.py` nutzt nur die Key-Tupel.

**Eigener Punkt, der im Review fehlte:** Ein Constraint nur auf `band_low` wäre die halbe Lösung — er würde den Key faktisch auf `medium` festnageln und damit überflüssig machen. Wer die Lücke wirklich schliessen will, entfernt `band_low` und leitet die Untergrenze ab. Umgekehrt präzisiert: „ausgeliefert ohne Stufe 3" ist per se kein Fail-open — alles über `band_high` ist genau das, per Design. Was Punkt 1 zu Recht trifft, ist die Asymmetrie zwischen einem Loch am unteren und einem am oberen Rand.

Antwortentwurf vorgelegt, nichts gepostet.

---

## 10 — Nutzer

> Könnte Punkt 1 zusammen mit T-28 umgesetzt werden? Dann wäre ich eher für einen Kommentar dort als ein eigenes Issue

### Claude

**Nein — jedenfalls nicht so.** T-28 ([#35](https://github.com/tsorer/LearnFlow/issues/35)) nachgelesen: es umfasst ausschliesslich 20 **Out-of-Corpus**-Fragen plus CI-Lauf. Genau diese Fragen erreichen Stufe 3 nie — sie werden am Retrieval-Gate unterdrückt, wie im Live-Lauf dieser Sitzung schon zu sehen war (`llm_calls: []`, Stufen 2–3 `ran=False`). Ein Kommentar dort mit „entscheiden wir mit T-28" wäre ein Versprechen, das T-28 nicht einlösen kann.

Die Frage betrifft **ausgelieferte** Antworten und bräuchte die In-Corpus-Hälfte, also das Gold-Dataset aus ADR-009. Vorschlag: Kommentar an T-28, aber ehrlich gerahmt — „T-28 baut die Harness, diese Frage wartet auf deren In-Corpus-Erweiterung" — und kein eigenes Issue, weil der dauerhafte Eintrag ohnehin in ADR-008 steht.

---

## 11 — Nutzer

> Die md-Dateien aus LearningCorpus sollten in die Db, oder was soll das Issue für den Gold-dataset machen?

### Claude

**Korrektur der eigenen Aussage von zuvor:** „Dafür gibt es kein Issue, die In-Corpus-Hälfte hat keinen Träger" war falsch. `LearningCorpus/` zum ersten Mal geöffnet — das Gold-Dataset **existiert bereits**: drei Sets, eines je Korpus-Dokument (SKOS, EU AI Act, SAMW), zusammen rund 79 Fragen mit `reference_answer` und `expected_source`, gleiches Schema.

**Zur Frage: nein.** In `LearningCorpus/` liegen zwei Arten von Artefakt. Die drei **PDFs** sind der Korpus und gehören in die DB (teils schon dort: die 206 Chunks). Die **Eval-Dateien** sind Test-Fixtures und bleiben im Repo — drei Gründe: sie sind die Erwartung, nicht die Daten unter Test; CI bräuchte sonst eine geseedete DB, um zu wissen, was sie behaupten soll; ihr Lebenszyklus ist git, nicht Alembic.

**Ein Detail fürs Verdrahten:** Alle Einträge tragen `expected_source_id: TBD`. Als UUID einzutragen wäre fragil — `chunks.id` wird bei jeder Neu-Indexierung neu vergeben, das Gate würde rot, ohne dass sich die Qualität geändert hat. Die Referenz muss stabil sein (`filename`/Seite), was `expected_source` in Prosa bereits enthält.

---

## 12 — Nutzer

> Ja, bitte Punkt 2 umsetzen, den #35-Kommentar posten, die Issues anlegen und zum Abschluss die PR-Antwort posten.

### Claude

Alle vier Aufträge ausgeführt:

- **Punkt 2:** Die beiden Config-Reads zu einem Round-Trip zusammengelegt (Commit `283a8f6`), mit erhaltener Fehlersemantik — unbrauchbarer Wert wirft weiterhin, fehlender Key fällt weiterhin auf den Default.
- **[#35](https://github.com/tsorer/LearnFlow/issues/35)-Kommentar** gepostet, mit der ehrlichen Rahmung.
- **Zwei Issues angelegt:** [#95](https://github.com/tsorer/LearnFlow/issues/95) (T-47, Gold-Dataset konsolidieren und Quellreferenz-Schema festlegen) und [#96](https://github.com/tsorer/LearnFlow/issues/96) (T-48, fachliche Abnahme).
- **PR-Antwort** an [#93](https://github.com/tsorer/LearnFlow/pull/93) gepostet.

---

## 13 — Nutzer

> Nein, nur Push. Vor dem Erstellen des PR ein Squash machen, damit der Review nur ein Commit sieht. Wenn es Korrekturen gibt, diese immer einzeln pushen, damit die Korrekturen nachvollziehbar sind --> Also hier nur ein push und kein Squash.

### Claude

**Nichts zu tun** — beide Commits waren bereits auf `origin`, der Branch in sync (`0` ungepushte Commits). Das eigene Squash-Angebot war damit in beide Richtungen falsch: unerwünscht *und* ein Rewrite bereits veröffentlichter Historie.

Die Regel als Memory festgehalten: Squash **vor** `gh pr create`, damit der Review einen Commit sieht; **nach** dem PR jede Korrektur als eigener Commit, einzeln gepusht, auch nicht vor dem Merge aufräumen. Begründung des Nutzers: Erst- und Zweit-Review lesen Verschiedenes — der zweite will sehen, was auf sein Feedback hin passiert ist.

---

## 14 — Nutzer

> Bitte den Chatverlauf möglichst Wortgetreu nach Frank/Prompts exportieren

### Claude

Transkript der Sitzung (`1c6d5e88-…jsonl`) statt Rekonstruktion aus dem Gedächtnis verwendet; Nutzer-Prompts byte-genau daraus übernommen. Bestehende Export-Konvention aus `Frank/Prompts/` übernommen (Kopf mit Datum/Branch/Gegenstand/Ergebnis, nummerierte Abschnitte, Prompts wörtlich, Antworten als Zusammenfassung).

Vor dem Schreiben des Ergebnis-Kopfes den tatsächlichen Endstand auf GitHub geprüft, weil der Verlauf des vorletzten Auftrags aus dem Kontext gefallen war — `#35`-Kommentar, Issues #95/#96 und PR-Antwort waren alle vorhanden.

---
