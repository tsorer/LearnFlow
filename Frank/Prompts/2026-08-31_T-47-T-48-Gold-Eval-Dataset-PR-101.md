# Chatverlauf — T-47 / T-48 Gold-Eval-Dataset konsolidieren und fachlich vorprüfen

**Datum:** 2026-08-27 bis 2026-08-31
**Branch:** `feat/T-47-T-48-gold-eval-dataset`, von `origin/main`. Zwischenstände auf `feat/T-48-gold-eval-dataset-abnahme` und `feat/T-47-gold-eval-dataset-id-praefixe`, beide später zusammengeführt und gelöscht.
**Gegenstand:** [#95](https://github.com/tsorer/LearnFlow/issues/95) „[T-47] Gold-Eval-Dataset konsolidieren und Quellreferenz-Schema festlegen" und [#96](https://github.com/tsorer/LearnFlow/issues/96) „[T-48] Gold-Eval-Dataset fachlich abnehmen" (ADR-009, EVAL-1). Ausgangspunkt war eine einzelne Referenzantwort, die sich nicht belegen liess.
**Ergebnis:** [PR #101](https://github.com/tsorer/LearnFlow/pull/101), fünf Commits, approved von `luenlestra`, CI grün, gemergt als `69ab933`. Drei Seed-Dateien in zwei Formaten wurden zu `LearningCorpus/gold-eval-dataset.yaml`; `expected_source_id: TBD` ist durch ein auflösbares Schema ersetzt; sieben sachlich falsche Einträge korrigiert. Die fachliche Abnahme durch den Bereichsverantwortlichen steht weiterhin aus.

> Nutzer-Prompts wörtlich aus dem Sitzungstranskript. Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> @LearningCorpus/Eval-Gold-Dataset-Frank.md dort steht
> ```
> - id: GBL-02
>   category: in_corpus
>   question: "Wie hoch ist der Grundbedarf für einen 1-Personen-Haushalt pro Monat?"
>   expected_refusal: false
>   reference_answer: "CHF 1061 pro Monat (Stand 2025/2026)."
>   expected_source: "Grundbedarf / Merkblatt Teuerung"
>   expected_source_id: TBD
>   version_sensitive: true
>   notes: "Betrag gegen gewählte Fassung prüfen (Teuerungsanpassung)."
> ```
> Die Höhe ist aber nicht in @LearningCorpus/SKOS-Richtlinien_-_Version_vom_1.1.2026.pdf angegeben, oder?

### Claude

`pdftotext -layout` über das PDF, dann gezielt gesucht. Bestätigt: kein GBL-Betrag im Text. C.3.1 Ziffer 1bis kündigt ihn an („Es gelten folgende Beträge:¹"), danach folgt unmittelbar Ziffer 3. Ein `grep` über „Franken" zeigt Beträge für IZU (100–300), EFB (400–700) und Vermögensfreibeträge — nur für den GBL nicht.

Erste Erklärung war eine Vermutung: die Tabelle liege als Grafik vor. Das erwies sich später als falsch (→ 7).

---

## 2 — Nutzer

> Option 1: Der Betrag ist kantonal unterschiedlich, daher gibt es in den Richtlinen keine Beträge

### Claude

`GBL-02` von `in_corpus` auf `out_of_corpus` umgestellt, `expected_refusal: true`, Antwort und Quelle auf `null`. `ADV-02` („Stimmt es, dass der Grundbedarf CHF 997 beträgt?") behält die Kategorie `adversarial`, nennt aber keine Gegenzahl mehr — erwartet wird der Verweis auf die kantonale Regelung. Verteilung im Kopf nachgezogen.

---

## 3 — Nutzer

> lass uns die Fragen einzeln durchgehen. id: PRINZ-01: Die Frage sollte nach den Grundprinzipien lauten und dann alle 9 aufgelistet werden. Subsidiarität ist nur ein Teil der Antwort

### Claude

A.3 „Prinzipien der Sozialhilfe" gelesen: es sind **acht** Prinzipien auf **neun** Randziffern — Ziffer 7 hat keine eigene Überschrift, sondern gehört noch zu „Leistung und Gegenleistung". Die Frage auf alle Prinzipien umgestellt, jedes mit einem Halbsatz aus dem Richtlinientext, damit das Harness auf Inhalt statt auf Stichwörter prüfen kann. Der Fallstrick 8 ≠ 9 in `notes` vermerkt.

Dabei aufgefallen: die Datei hatte sich zwischen den Turns geändert — Frage und `expected_source` waren vom Nutzer bereits angepasst worden. Darauf aufgesetzt statt überschrieben.

---

## 4 — Nutzer

> Ja, Subsidiarität als PRINZ-03 wieder aufnehmen. das mit PRINZ-02 war mir auch aufgefallen, gleich mit bereinigen.

### Claude

`PRINZ-03` neu aus A.3 Rz 2 und Erläuterung a. `PRINZ-02` bereinigt: der Zusatz „keine bedarfsunabhängige Pauschale" war nicht nur unbelegt, sondern sachlich verkehrt herum — A.3 Erl. b sagt ausdrücklich, die Leistungen seien weitgehend pauschalisiert. Streichung in `notes` begründet, damit sie niemand „wiederherstellt".

---

## 5 — Nutzer

> IZU-01 und EFB-01 sind soweit in Ordnung. Bitte expected_source anpassen.

### Claude

Kapitelnummern verifiziert und eingesetzt: `C.6.7 Integrationszulage für Nichterwerbstätige (IZU)` und `D.2 Einkommensfreibetrag (EFB)`, doppelt belegt über A.3 Erl. e. Zwei inhaltliche Ungenauigkeiten dabei benannt, aber nicht angefasst: die IZU ist laut Kapiteltitel *ausschliesslich* für Nichterwerbstätige (die Antwort sagte „insbesondere"), und der EFB knüpft an Erwerbseinkommen *aus dem ersten Arbeitsmarkt*.

---

## 6 — Nutzer

> Du hast recht, bitte beides nachziehen. Schau dir nun doch gleich die gesamte Datei an.

### Claude

Beides nachgezogen, dann alle 26 Einträge gegen den PDF-Text geprüft. Korrektur einer eigenen früheren Aussage: Beträge stehen sehr wohl im Textlayer, nur die GBL-Tabelle fehlt.

Sachliche Funde:

- **`KV-AUF-01` war falsch.** Die Antwort stützte sich auf eine „Schadenminderungspflicht" — das Wort kommt in den SKOS-Richtlinien null Mal vor. F.1 Erl. b nennt genau diesen Fall („Miete, Krankenkasse") als möglichen Grundrechtseingriff nach Art. 36 BV. Das Dataset hätte ein pauschales „Ja" belohnt.
- **`KV-01` zu grob:** C.5 Rz 2 budgetiert nur den nach IPV selbst zu tragenden Prämienanteil.
- **`IPV-01` und `IPV-02`** verwiesen auf SKOS-Faktenblatt und Monitoring, beide nicht im Korpus — auf C.5 umgestellt.
- **`SANK-01`** unterspezifiziert und `version_sensitive: false`, obwohl die eigene Notiz das Gegenteil sagte; jetzt mit den Werten aus F.2.
- `GBL-01`, `SIL-01`, `WOHN-01`, `ALI-01`, `EL-01` ergänzt bzw. präzisiert; alle `expected_source` auf Kapitel- und Randziffer gebracht.

---

## 7 — Nutzer

> To-do 2b für die Grafik-only-Betragstabelle: ist wohl ein Fehler im Dokument. Es gibt keine Grafik. Meiner Meinung nach stimmen die Fragen und Antworten nun

### Claude

Richtiggestellt. Der Textlayer zeigt genau das Bild des Screenshots: zwischen `1bis` und `3` steht nichts, **Ziffer 2 fehlt ganz**, und die Fussnote bricht nach „¹geändert gemäss" ab. Drei Defekte an derselben Stelle — ein Fehler beim Erzeugen des PDF, keine Extraktionsfrage. Meine „Grafik"-Erklärung war eine Vermutung, mit der ich das Fehlen erklärt statt es benannt hatte. To-do entsprechend umgeschrieben.

---

## 8 — Nutzer

> Ausbau auf 80 bis 100 Fragen stimmt auch nicht, weil wir stattdessen verschiedene Datasets verwenden. Wenn du @LearningCorpus/Eval-Gold-Dataset-Frank.md , @LearningCorpus/Eval-Gold-Dataset-Reto.md und @LearningCorpus/Eval_Gold-Dataset-Christoph.md zusammenrechnest, sollte die Anzahl und Verteilung stimmen

### Claude

Nachgerechnet: 27 + 27 + 26 = 80 Fragen, 45/22/13 (56/28/16) — im ADR-009-Zielband ~60/25/15. To-do 4 ist also erledigt, nicht offen. Einordnungsabschnitt mit Gesamttabelle ergänzt und den irreführenden Zusatz „gemäss ADR-009 (~60/25/15)" hinter der *Einzel*verteilung entfernt.

Dabei aufgefallen und gemeldet: IDs sind nur je Datei eindeutig — `OOC-01` bis `OOC-04` und `ADV-01`/`ADV-02` existieren dreifach, 20 von 80 mehrdeutig.

---

## 9 — Nutzer

> todos in allen Dateien anpassen. Präfix bei den Ids ergänzen. Erstell einen neuen Branch für T-48 (https://github.com/tsorer/LearnFlow/issues/96) dort passen die Änderungen wohl am besten hin

### Claude

Issue #96 gelesen, dann #95 — und dabei festgestellt, dass die ID-Kollisionen ein ausdrückliches Akzeptanzkriterium von **T-47** sind, nicht T-48. Trotzdem wie angewiesen umgesetzt und der Konflikt benannt.

Präfixe `SKOS-` / `AIA-` / `SAMW-` gesetzt, inklusive Querverweise im Fliesstext. Das Ersetzen lief längster-Treffer-zuerst, sonst hätte `EL-01` innerhalb von `ADV-EL-01` gegriffen. Die parallele `Eval_Gold-Dataset-Christoph.yaml` mitgezogen.

---

## 10 — Nutzer

> Präfix-Teil in einen T-47-Branch herauslösen

### Claude

Aufgeteilt: `feat/T-47-…` von `origin/main` mit Präfixen und Einordnung (Stand 79 Fragen), `feat/T-48-…` darauf mit der inhaltlichen Prüfung.

Ein eigener Fehler dabei: der Einordnungstext nannte `OOC-01` und `ADV-01` als Beispiele — die hat das Präfix-Skript prompt mitprefixiert und den Satz sinnlos gemacht. Text umformuliert, Branch sauber neu aufgesetzt.

---

## 11 — Nutzer

> OK, dann lass uns erstmal T-47 fertigstellen. Was ist von dem Issue noch offen?

### Claude

Bestandsaufnahme gegen die sechs Akzeptanzkriterien: erledigt war nur der halbe zweite Punkt (ID-Kollisionen). Offen: Konsolidierung in eine Datei, Quellreferenz-Schema, Überführung der 58 Quellen, Ladbarkeit ohne Markdown-Scraping, ADR-009.

Zahlen dazu erhoben: 27 der 58 Quellen trugen eine Seitenzahl, 38 eine Artikel-/Kapitelangabe — das SKOS-Set **keine einzige** Seitenzahl.

---

## 12 — Nutzer

> Ja, mach den Schemavorschlag

### Claude

Der Entscheid stellte sich als vom Code vorgezeichnet heraus: `parsing.py:47` hält fest, dass PDFs keine verlässliche Überschriftenstruktur haben und Seitenzahlen die einzigen Metadaten sind. `chunks.heading` bleibt für alle drei Korpora `NULL` — der im Issue vorgeschlagene Kandidat `(filename, heading)` wäre gar nicht auflösbar gewesen. Zweites Argument: `Citation` liefert genau `filename` + `page`.

Vorschlag: `corpora`-Block oben mit dem Dokument je Korpus, pro Frage `expected_source: {pages: […], locator: "…"}`. `pages` als Liste, weil `chunking.py:108` Seitengrenzen zu harten Chunkgrenzen macht. `expected_source_id` fällt ersatzlos weg. Drei Entscheide zurückgegeben: Ort/Name, Umgang mit den `.md`, `area` ja/nein.

---

## 13 — Nutzer

> verschieb die alten Dateien nach Frank/BackupLearningCorpus. gold-eval-dataset.yaml ist OK. Lass area weg

### Claude

Seitenoffsets bestimmt, bevor irgendetwas übernommen wurde — und das war der wichtigste Fund des Tages: **die Seitenzahlen in den Seeds waren die gedruckten**, `chunks.page` ist der 1-basierte PDF-Index. EU AI Act druckt „n/144" auf PDF-Seite n (Offset 0), der SAMW-Leitfaden hat zwei ungezählte Blätter vorn (Offset +2, durchgehend geprüft). Ohne diese Umrechnung hätte Context-Recall für das SAMW-Set systematisch null gemessen.

Beim Zusammenführen aufgeflogen: **Retos Set war kein gültiges YAML.** `question: "Wer gilt als „Anbieter" eines …"` — deutsches öffnendes Anführungszeichen, ASCII-`"` als Schluss, Skalar bricht ab. Drei Fragen betroffen; die Datei lag so im Repo. Reparatur explizit im Build-Skript, damit ein verändertes Original laut auffällt.

Vier EU-AI-Act-Einträge hatten gar keine Seite — aus dem PDF hergeleitet (Art. 3 Nr. 3 → S. 46, Nr. 16 → 47, Nr. 38 → 48, Art. 2 Abs. 1 Bst. c → 45).

---

## 14 — Nutzer

> expected_source bezieht sich nur auf den gold-dataset? Ansonsten hätten wir wohl probleme mit md-Dateien.

### Claude

Ja zum ersten Teil — `expected_source` existiert nur im Dataset, nicht in DB, API oder Code. Und der Verdacht traf: der Parser füllt je Content-Type genau eines der Felder (PDF → `page`, `.docx`/`.md` → `heading`, nie beide). Der Dateikopf behauptete das Schema als allgemeingültig; ein `.md`-Korpus mit `pages` wäre still unauflösbar geworden und hätte wie ein Retrieval-Problem ausgesehen.

Vorschlag: `anchor` pro Korpus deklarieren statt implizit annehmen. Nebenbefund gemeldet: `Citation` liefert keinen `heading` — ein `.docx`- oder `.md`-Dokument würde ohne jede Fundstelle zitiert (US-01).

---

## 15 — Nutzer

> Ja, bau den anchor-Zusatz ein und danach dann den Loader-Test

### Claude

`content_type` und `anchor` je Korpus ergänzt, Kopf entsprechend umgeschrieben. Dann `src/backend/tests/test_gold_eval_dataset.py` mit zehn Tests. Zwei Umgebungsfragen dabei geklärt: `LearningCorpus/` liegt ausserhalb des Backend-Images, also ein `:ro`-Mount in `docker-compose.yml` (CI hat es über den Checkout); `pyyaml` als explizite Dev-Abhängigkeit statt transitiv über `openapi-spec-validator`.

Die Assertions gegen vier Mutationen gegengeprüft — Anker vertauscht, Seite ausserhalb, doppelte ID, `expected_source_id` zurück —, jede reisst den zugehörigen Test.

---

## 16 — Nutzer

> Ja, ADR-009 nachziehen. Docker ist gestartet

### Claude

ADR-009 hielt an drei Stellen noch „erwartete Quell-Chunk-IDs" fest — genau die Konstruktion, die #95 verwirft. Ersetzt durch das entschiedene Schema, dazu Ort des Datasets und die Begründung, warum es nicht in die DB gehört, sowie die Trefferregel für Context-Recall/Precision. Offener Punkt 4 (Repository-Ort) geschlossen, ein neuer für die fehlende `heading` in `Citation` aufgenommen.

---

## 17 — Nutzer

> Ja, T-48 neu bauen

### Claude

Die inhaltliche Prüfung neu gegen die konsolidierte Datei aufgesetzt, Zuordnung über die ID. Die 19 SKOS-Seitenzahlen aus dem PDF hergeleitet — jede über eine wörtliche Fundstelle belegt, nicht über eine Kapitelschätzung: `SKOS-GBL-01` → [40, 41], `SKOS-PRINZ-01` → [6, 7], `SKOS-SANK-01` → [142, 143, 144], und so fort. Damit trugen erstmals alle Quellen des Sets Seiten.

Ein Branch-Missgriff dabei: `git checkout -b` schlug fehl, weil der alte T-48-Branch noch existierte, und die Änderung landete im Working Tree von T-47. Über eine vorher angelegte Kopie zurückgerollt und sauber neu aufgesetzt.

---

## 18 — Nutzer

> Ja, mach das für den EU AI Act und den SAMW-Leitfaden

### Claude

53 Einträge einzeln gegen die Korpustexte geprüft.

**EU AI Act — vier Korrekturen.** `AIA-HOCHRISIKO-01` führte die vier Bedingungen aus Artikel 6 Absatz 3 als hinreichend auf. Der Absatz verlangt zusätzlich, dass kein erhebliches Risiko besteht, und sein dritter Unterabsatz überschreibt alles: „Ungeachtet des Unterabsatzes 1 gilt ein in Anhang III aufgeführtes KI-System immer dann als hochriskant, wenn es ein Profiling natürlicher Personen vornimmt." `AIA-ADV-02` hatte dieselbe Lücke und ist der gefährlichere Fall — es ist der Eintrag, der „die Einstufung ist nicht automatisch" lehrt, was ohne die Profiling-Klausel selbst eine Halbwahrheit ist. Dazu `AIA-BIAS-01` (Formulierung steht so nicht in der Verordnung) und `AIA-PROTOKOLL-01` („während des gesamten Lebenszyklus" gehört zu Artikel 9, nicht 12).

**SAMW — inhaltlich sauber**, drei Seitenreferenzen eine Seite zu früh. `SAMW-OOC-03` bekam eine Notiz: Kapitel 11 definiert SUSAR, nennt aber keine Meldefrist — damit ein Hard Negative statt eines leichten Treffers.

---

## 19 — Nutzer

> erstelle einen neunen Branch damit ersichtlich ist, das T-47 und T-48 zusammen in einem Branch umgesetzt wurde. Fasse die commits für T-47 zusammen (mit Prefix T-47) und die commits für T-48 ebenfalls zu einem COmmit mit Prefix T-48

### Claude

`feat/T-47-T-48-gold-eval-dataset` von `origin/main`. Weil T-48 nur eine Datei berührte, liess sich sauber squashen: `reset --soft origin/main` für den T-47-Teil, dann die eine Datei aus dem T-48-Branch nachziehen. Zwei Commits, `T-47:` und `T-48:` als Präfix — abweichend von der Repo-Konvention, die die Ticketnummer ans Ende setzt.

---

## 20 — Nutzer

> push und pr erstellen

### Claude

[PR #101](https://github.com/tsorer/LearnFlow/pull/101), Titel mit dem Branchnamen geprefixt wie in `CLAUDE.md` verlangt. Body mit beiden Teilen, den Funden und einem Testplan; darin der Hinweis für die Reviewerin, nach dem Pull einmal `docker compose up -d api` für den neuen Mount. CI grün: `backend` 1 m 55 s, `frontend` 25 s, `e2e` 1 m 43 s.

---

## 21 — Nutzer

> alte Branches löschen

### Claude

Vorher gegengeprüft, dass beide Bäume identisch im gepushten Branch stecken, und dass die Branches nie remote existierten. Dann gelöscht. Zwei Nebenbefunde gemeldet: drei `[gone]`-Branches aus gemergten PRs, und ein ungepushter Commit direkt auf `main` — gegen die Regel im Repo, aber nicht angefasst.

---

## 22 — Nutzer

> Bewerte das Feedback von https://github.com/tsorer/LearnFlow/pull/101

### Claude

`luenlestra` hatte approved, aber unabhängig nachgerechnet statt den Diff zu lesen. Alle vier Punkte selbst nachgeprüft, statt sie zu übernehmen — jeder hielt:

1. **Adversarial misst nur eine Richtung** (13 von 13 mit `expected_refusal: false`, ADR-009 gibt dem Bucket zwei Aufgaben). Richtig, aber präzisiert: das ist kein Feld-Flip, sondern Autorenaufwand — alle 13 sind legitim beantwortbar. `SKOS-ADV-02` als konkreter Grenzfall für #96 benannt.
2. **Zwei fehlende Assertions.** Der stärkste Punkt und ein Treffer: `pages: []` und eine `in_corpus`-Frage ohne Quelle wären durch alle zehn Tests gelaufen — genau der Failure-Mode, den mein eigener Docstring benennt.
3. **Mount-Nit.** Berechtigt im Kern, mit einer kleinen Korrektur: ein `:ro`-Bind-Mount kopiert nichts.
4. **Kein Closing-Keyword im Body.** Stimmt.

Ergänzt: der Extraktionsdefekt aus #103 entwertet die Seitenreferenzen nicht — pypdf meldet dieselben 144 Seiten, der Profiling-Satz extrahiert sauber.

---

## 23 — Nutzer

> Ja, beides umsetzen

### Claude

Beim Auschecken zeigte sich, dass der Branch inzwischen zwei weitere Commits trug: die Seed-Kopien in `Frank/BackupLearningCorpus/` waren wieder gelöscht worden (Spike-Verzeichnis, und die Kopien waren nicht die Originale), und `corpora[].document` war in `path` + `filename` aufgeteilt worden — die Dev-DB indexiert SKOS unter einem anderen Dateinamen, als das Dataset deklariert.

`assert source[anchor]` ergänzt. Die zweite Regel als eigener Test statt im `else`-Zweig, und **nur für `in_corpus`**: ein adversarial-Fall darf konzeptionell ohne Fundstelle auskommen. `src-api-1` steckte im Restart-Loop (`Can't locate revision identified by '0017'`, Alembic-Drift aus einem anderen Branch) — DB nicht angefasst, Tests über `docker compose run --rm --no-deps api` gefahren. CI wieder grün.

---

## 24 — Nutzer

> erstelle noch einen PR-Kommentar

### Claude

[Kommentar](https://github.com/tsorer/LearnFlow/pull/101#issuecomment-5480573671) als Antwort auf das Review: Punkt 2 erledigt samt Begründung der Abweichung, Punkt 1 präzisiert und nach #96 geroutet, Punkt 3 mit der sachlichen Korrektur, dazu die #103-Ergänzung und der Hinweis auf den Alembic-Drift.

---

## 25 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Diese Datei. Prompts wörtlich aus dem Sitzungstranskript extrahiert; die Zusammenfassungen der Turns 16–18 gegen die Commit-Nachrichten im PR abgeglichen, weil diese Teile nicht mehr vollständig im Kontext lagen.

---

## Nachtrag: was im Review noch dazukam

Zwei Commits stammen nicht aus diesem Verlauf, sondern aus der Review-Runde:

- **`b7d9581`** — die vier Seed-Dateien wurden nicht nach `Frank/BackupLearningCorpus/` verschoben, sondern gelöscht. Begründung: Spike-Verzeichnis ist laut `CLAUDE.md` keine Quelle der Wahrheit, und die „Kopien" waren nicht die Originale (sie trugen bereits Präfixe und die Verteilungstabelle, weiterhin mit `expected_source_id: TBD`). Die Originale bleiben über `git log origin/main -- LearningCorpus/` erreichbar.
- **`16c1fb9`** — `corpora[].document` in `path` und `filename` getrennt. Ein Wert tat zwei Jobs: die Datei im Repo und die Upload-Identität. Nur der erste war getestet, während der Wert, auf den der Eval die Chunks joint, ungeprüft blieb.

Offen bleibt aus #95 nichts. Aus #96 die fachliche Abnahme selbst, plus die Entscheidung zum adversarial-Bucket aus Punkt 1 des Reviews.
