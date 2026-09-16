# R04 — Regel 3 und 4 als eine Entscheidung

> **Status 2026-09-16: abgeschlossen, alle fünf Profile gemessen.**
> **Ergebnis: die Regel bleibt.** Vier von fünf Profilen verbessern sich, das fünfte
> (`ministral3-local`) verschlechtert sich aus einem Grund, der nicht in dieser Regel
> liegt, sondern in Stufe 3 — daraus wird R05. Begründung in Abschnitt 6.

Vorgehen und Begriffe: `00_Vorgehen.md`. Vorrunden: `R00_Baseline.md`,
`R01_Satzzerlegung.md`, `R02_Zitierformat.md`, `R03_Praemissen.md`.
Rohdaten: `kennzahlen.csv` (Zeilen `R04,…`), Einordnung jeder Abweichung:
`labels/R04.csv`, generierter Bericht: `berichte/R04_Modellvergleich.md`.
Auswertungsskripte: `werkzeuge/`.

---

## 0. Was man wissen muss, um diese Runde zu lesen

Damit dieses Dokument für sich stehen kann, in Kurzform:

**Die Pipeline.** LearnFlow beantwortet Fragen ausschliesslich aus hochgeladenen
Dokumenten. Eine Frage läuft durch vier Stufen, jede darf verweigern (ADR-008,
fail-closed — im Zweifel keine Antwort):

| Stufe | prüft | verweigert, wenn … |
|---|---|---|
| 0/1 Retrieval | Suche nach Textabschnitten | nichts ausreichend Ähnliches gefunden wird |
| 2a Modell | das Sprachmodell formuliert aus fünf Abschnitten | es selbst mit `WEISS_NICHT` antwortet |
| 2b Coverage | trägt jede Aussage einen Beleg `[n]`? | weniger als 50 % der Aussagen belegt sind |
| 3 Self-Check | dasselbe Modell prüft seine eigene Antwort | es nicht mit `GEDECKT` urteilt |

Stufe 3 läuft **nicht immer**, sondern nur wenn die Gesamtkonfidenz im Band 0,45–0,75
liegt: sehr sichere und sehr unsichere Antworten werden nicht geprüft.

**Das Messfeld.** 80 Fragen aus dem fachlich abgenommenen Gold-Dataset: 45 `in_corpus`
(Antwort steht im Korpus, erwartet wird eine Antwort), 22 `out_of_corpus` (Antwort steht
nicht im Korpus, erwartet wird eine Verweigerung), 13 `adversarial` (Fangfragen, teils mit
falscher Annahme). 22 der 80 Fragen liegen im **Holdout** und werden bis zur Schlussrunde
nicht ausgewertet; die 58 übrigen sind das **Entwicklungs-Set**.

**Die zwei Kennzahlen, um die es geht.**

- **Out-of-Corpus-Refusal** — Anteil der 22 Fragen ohne Antwort im Korpus, bei denen die
  Pipeline verweigert hat. Hoch ist gut, Zielwert ≥ 90 % (ADR-009).
- **False-Suppression** — Anteil der Fragen mit Antwort im Korpus, bei denen die Pipeline
  trotzdem verweigert hat. Tief ist gut, Zielwert ≤ 15 %. Das ist die Kehrseite: eine
  Pipeline, die alles verweigert, hat perfekte Refusal-Rate und ist unbrauchbar.

**Die fünf Profile.** `openai` = `gpt-4o-mini` über OpenAI Direct, das ausgelieferte
Referenzmodell. Dazu vier lokale Modelle über Ollama auf derselben Testhardware:
`qwen3-local` (qwen3:8b), `gpt-oss-local` (gpt-oss:20b), `ministral3-local`
(ministral-3:14b), `gemma4-local` (gemma4:26b). Alle mit Temperatur 0 und identischen
Schwellen — die Profile unterscheiden sich **nur** im Modell und in Zeit-/Token-Budgets.

**Laufzeiten sind hier kein Auswahlkriterium** (`00_Vorgehen.md`, Abschnitt 5a). Sie werden
mitgeschrieben, um die Zielhardware abzuschätzen, nicht um ein Modell zu verwerfen.

---

## 1. Worum es in dieser Runde geht

Zwei Vorrunden haben je eine Hälfte desselben Problems offengelegt:

- **R00/R03 — Übervorsicht.** Fragen, deren Annahme der Kontext widerlegt («der
  Belmont-Report nennt fünf Prinzipien» — er nennt drei), werden verweigert statt
  richtiggestellt. R03 hat versucht, das mit einer **angehängten Ausnahme** zu lösen
  («Widerlegt der Kontext eine Annahme der Frage, …»). Wirkung: keine. Der Befund von
  R03 war, dass eine Ausnahme hinter der Anweisung «antworte ausschliesslich mit
  WEISS_NICHT» von keinem Modell gelesen wird.
- **R00 — Teilantworten auf Fragen ohne Antwort im Korpus.** `gemma4` und `qwen3` bauen
  aus thematisch verwandten Passagen eine Teilantwort mit ausdrücklich benannter Lücke.
  Das war nach der damaligen Regel 4 *erlaubt* — und gerade deshalb verfehlten beide die
  90-%-Grenze beim Out-of-Corpus-Refusal.

R04 baut deshalb die Regeln 3 und 4 **um**, statt sie zu ergänzen.

### 1.1 Hypothese

> Werden Verweigerung, Richtigstellung und Teilantwort zu **einer** Entscheidung mit drei
> ausdrücklich getrennten Fällen, steigt der Anteil richtiggestellter Annahme-Fragen **und**
> die Out-of-Corpus-Refusal-Rate (weil «Ähnliches zu einem anderen Gegenstand» ausdrücklich
> keine Teilantwort mehr ist), ohne dass die False-Suppression steigt.

### 1.2 Die Änderung — eine Stellschraube

Regelblock 3/4 des Generierungs-Prompts in `app/services/generation.py`, Commit
`b7246f9`, festgehalten durch
`tests/test_generation.py::test_the_three_cases_are_decided_before_answering`.
Alles andere — Retrieval, Schwellen, Satzzerlegung, Self-Check-Prompt — unverändert.

| vorher (bis R03) | R04 |
|---|---|
| **3.** Deckt der Kontext die Frage nicht ab, antworte ausschliesslich mit WEISS_NICHT — ohne Begründung, ohne weiteren Text.<br>**4.** Ist nur ein Teil der Frage belegt, beantworte diesen Teil und benenne ausdrücklich, was der Kontext nicht abdeckt.<br>*(R03 hatte zusätzlich eine angehängte Ausnahme für widerlegte Annahmen.)* | **3.** Entscheide zuerst, welcher der drei Fälle vorliegt:<br>a) Der Kontext **widerlegt eine Annahme** der Frage — etwa eine falsche Anzahl oder eine Regel, die so nicht besteht: stelle die Annahme mit Beleg richtig.<br>b) Der Kontext beantwortet die Frage **ganz oder in einem Teil**: antworte auf diesen Teil.<br>c) Der Kontext trägt zur gestellten Frage **nichts** bei — auch dann nicht, wenn er Ähnliches zu einem anderen Gegenstand enthält: antworte ausschliesslich mit WEISS_NICHT, ohne Begründung, ohne weiteren Text.<br>**4.** Im Fall b) benenne ausdrücklich, was der Kontext nicht abdeckt. |

---

## 2. Die Messung

Ein Lauf je Profil, alle 80 Fragen, Code-Stand `b7246f9`, dieselbe Hardware, Rechner
sonst unbenutzt. Die lokalen Modelle wurden zwischen den Läufen aus dem VRAM entladen
(sonst CUDA-OOM, siehe `00_Vorgehen.md`).

| Profil | Lauf Out-of-Corpus | Lauf In-Corpus | LLM-Zeit | Median je Antwort |
|---|---|---|---|---|
| `openai` | 2026-09-16T04-52-06Z | 2026-09-16T04-50-07Z | 122 s | 1,2 s |
| `qwen3-local` | 2026-09-16T05-00-52Z | 2026-09-16T04-52-42Z | 584 s | 5,9 s |
| `gpt-oss-local` | 2026-09-16T05-19-11Z | 2026-09-16T05-03-00Z | 1125 s | 10,4 s |
| `ministral3-local` | 2026-09-16T13-27-52Z | 2026-09-16T12-48-47Z | 2565 s | 16,0 s |
| `gemma4-local` | 2026-09-16T15-28-34Z | 2026-09-16T13-32-22Z | 7945 s | 58,3 s |

**Vergleichsbasis.** Für vier Profile ist es R03. `gemma4-local` war in R02a und R03
pausiert (Laufzeit), seine Vergleichsbasis ist deshalb **R01** — der gemessene Unterschied
enthält bei gemma4 also R02a (Zitierregel) *und* R04. Das ist bei jeder gemma4-Zahl unten
mitzulesen.

**Gültigkeit.** Vier der fünf Läufe sind vollständig sauber: alle Aufrufe
`finish_reason = stop`, keine leere Antwort, keine Endlosschleife (anders als `qwen3` in
R03). `gemma4-local` hat **zwei Messartefakte** — dazu Abschnitt 4.7.

---

## 3. Ergebnis: die Kennzahlen

### 3.1 Alle 80 Fragen

| Profil | Out-of-Corpus-Refusal | False-Suppression | Halluzination | Artefakte |
|---|---|---|---|---|
| `openai` | 90,9 % → 90,9 % | 24,4 % → **22,2 %** | 0 % (Pool 41) | 0 |
| `qwen3-local` | 59,1 % → **68,2 %** | 6,7 % → 6,7 % | 0 % (Pool 50) | 0 |
| `gpt-oss-local` | 90,9 % → **95,5 %** | 40,0 % → **37,8 %** | 0 % (Pool 33) | 0 |
| `ministral3-local` | 100 % → **95,5 %** | 31,1 % → **40,0 %** | 0 % (Pool 29) | 0 |
| `gemma4-local` (Basis R01) | 81,8 % → **86,4 %** | 6,7 % → **11,1 %** | 0 % (Pool 50) | **2** |

Die 11,1 % von gemma4 sind **fünf** von 45 In-Corpus-Fragen, davon **zwei** die
Messartefakte. Ohne sie: 6,7 %, also unverändert gegenüber R01.

Der Verlust von ministral (100 % → 95,5 %) ist **eine einzige Frage**: `SAMW-OOC-03`
(«Innert welcher Frist müssen SUSAR der Ethikkommission gemeldet werden?»). Diese Frage
ist ein bekannter **Gold-Fehler** — die Fristen 7 und 15 Tage stehen wörtlich im
SAMW-Leitfaden (PDF-S. 83), die erwartete Verweigerung ist also fachlich falsch (gemeldet
an T-48, Dataset absichtlich nicht geändert). Ministral hat sie in R04 vollständig und
korrekt belegt beantwortet. Als Verschlechterung zählt das nur gegen das Dataset.

### 3.2 Entwicklungs-Set (58 Fragen)

| Profil | Annahme-Fragen richtiggestellt | Out-of-Corpus verweigert | False-Suppression | Abweichungen |
|---|---|---|---|---|
| `openai` | 4 → **5 von 6** | 15 → 15 von 16 | 7 → **6 von 33** | 12 → 10 |
| `qwen3-local` | 5 → 5 von 6 | 10 → **11 von 16** | 1 → 1 von 33 | 9 → 10 |
| `gpt-oss-local` | 4 → **3 von 6** | 14 → **15 von 16** | 13 → **12 von 33** | 19 → 18 |
| `ministral3-local` | 3 → **2 von 6** | 16 → **15 von 16** | 8 → **11 von 33** | 12 → 17 |
| `gemma4-local` (Basis R01) | 6 → 6 von 6 | 12 → **13 von 16** | 2 → **4 von 33** | 8 → 9 |

### 3.3 Einordnung der 64 Abweichungen

Jede Abweichung von der Gold-Erwartung ist von Hand eingeordnet (`labels/R04.csv`),
daraus die beiden Achsen aus `00_Vorgehen.md`: **Urteilsfähigkeit** = Anteil inhaltlich
richtiger Entscheide, **Protokolltreue** = Anteil der Entscheide im geforderten Format
(je über alle 58 Fragen des Entwicklungs-Sets).

| Profil | Urteilsfähigkeit | Protokolltreue | Klassen |
|---|---|---|---|
| `openai` | 0,931 (R00: 0,931) | **0,931** (R00: 0,914) | F1:1 P2:1 S1:1 S2a:4 S3:2 S5:1 |
| `qwen3-local` | 0,931 (R00: 0,931) | **0,966** (R00: 0,948) | D:2 F1:2 P1:2 P2:2 S1:2 |
| `gpt-oss-local` | **0,948** (R00: 0,897) | 0,810 (R00: 0,810) | D:1 F1:1 P2:1 S1:2 S2a:9 S2b:2 S5:2 |
| `ministral3-local` | **0,931** (R00: 0,897) | **0,914** (R00: 0,862) | D:2 P3:1 S1:3 S2a:1 S2b:3 **S4:5** S5:2 |
| `gemma4-local` | 0,983 (R00: 0,983) | **1,000** (R00: 0,983) | A:2 D:2 P2:3 S1:1 S5:1 |

Über alle vier Prompt-Runden zusammen (R00 → R04) wird also **kein Profil auf einer der
beiden Achsen schlechter**, drei werden auf beiden besser.

Kurz zu den Klassen, die unten vorkommen (vollständige Tabelle in `00_Vorgehen.md`):
**P1** Verweigerung in Prosa statt `WEISS_NICHT` · **P2** Teilantwort mit benannter Lücke ·
**P3** `WEISS_NICHT` mitten im Fliesstext · **F1** Verwechslung (belegte Aussage zu einem
anderen Gegenstand) · **S1** Übervorsicht · **S2a** Sammelbeleg · **S2b** fremdes
Zitatformat · **S3** echte Deckungslücke · **S4** Self-Check-Fehlurteil · **S5** Retrieval ·
**A** Messartefakt · **D** Gold-Erwartung strittig.

**Bemerkenswert:** Die Klassen **S2c** und **S2d** — Fehler der *Pipeline* bei der
Satzzerlegung — kommen in R04 als Hauptklasse **kein einziges Mal** mehr vor. In R00 waren
es 8 Fälle über vier Profile. Das ist die nachträgliche Bestätigung von R01.

---

## 4. Was die Runde zeigt

### 4.1 Die Richtung stimmt bei vier von fünf Profilen

Die Refusal-Rate steigt genau dort, wo sie zu tief war — `qwen3` +9,1 pp,
`gemma4` +4,6 pp, `gpt-oss` +4,6 pp — und die False-Suppression sinkt dabei bei zwei
Profilen leicht, bei zwei anderen bleibt sie gleich. Das ist der klare Gegensatz zu R03,
wo *nichts* passierte: die Umstellung von «Regel plus Ausnahme» auf «eine Entscheidung mit
drei Fällen» ist der wirksamere Hebel.

`openai` bleibt bei 90,9 % und verbessert sich bei den Annahme-Fragen von 4 auf 5 von 6
(neu richtiggestellt: `SAMW-ADV-01`, das dem SAMW-Leitfaden unterstellte absolute Verbot).

**Der wichtigste Einzelbefund der Runde** ist aber nicht die Richtung, sondern **dass sie
nicht für alle gilt**. Dieselbe Prompt-Änderung, dieselben Schwellen, dieselben Fragen:
drei Modelle werden besser, eines bleibt gleich, eines wird deutlich schlechter. Modelle
sind an dieser Pipeline nicht austauschbar.

### 4.2 Der Preis der Regel: längere Antworten bei gleich viel Belegen

Der neue Regelblock ist deutlich länger und verlangt in Fall b) ausdrücklich, die Lücke zu
benennen. Beides zusammen macht die Antworten länger, **ohne** dass die Belege mitwachsen
(Entwicklungs-Set, nur Antworten mit Text):

| Profil | Antworten | Median Zeichen | Median Belege | Zeichen je Beleg | unbelegte Aussagen |
|---|---|---|---|---|---|
| `openai` | 37 → 42 | 342 → **426** | 1 → 1 | 178 → **194** | 27 % → **31 %** |
| `qwen3-local` | 47 → 44 | 265 → 268 | 2 → 2 | 111 → 118 | 2 % → 4 % |
| `gpt-oss-local` | 37 → 38 | 334 → 320 | 1 → 1 | 200 → **251** | 49 % → **57 %** |
| `ministral3-local` | 36 → 37 | 539 → **655** | 4 → **3** | 129 → **142** | 16 % → **27 %** |
| `gemma4-local` (Basis R01) | 43 → 39 | 369 → 381 | 3 → 3 | 141 → **119** | 10 % → **7 %** |

«Zeichen je Beleg» steigt bei vier von fünf Profilen — die Belegdichte sinkt, und weil
Stufe 2b genau die Belegdichte misst, sinkt die Coverage mit. Das ist der Mechanismus, über
den eine Prompt-Regel, die inhaltlich nichts falsch macht, die Unterdrückungsrate anhebt.

Die Ausnahme ist `gemma4`: dort **verbessert** sich die Belegdichte (141 → 119 Zeichen je
Beleg, unbelegte Aussagen 10 % → 7 %). Das ist kein Widerspruch, sondern die
Vergleichsbasis: gemma4 bekommt in diesem Vergleich die R02a-Zitierregel zum ersten Mal
mit, und deren Wirkung überwiegt die Verwässerung durch R04.

### 4.3 `ministral3-local`: die Kette, die die Runde für dieses Modell kippt

Ministral ist das einzige Profil, das sich klar verschlechtert (False-Suppression
31,1 % → 40,0 %). Die Ursache ist eine Kette aus drei Gliedern, und nur das erste ist die
R04-Regel:

1. **Längere Antworten, gleich viele Belege** (4.2): die Coverage fällt reihenweise von 1,0
   auf 0,5–0,85 — `AIA-DOKUMENT-01` 1,0 → 0,50, `SAMW-JUGENDLICHE-01` 1,0 → 0,50,
   `AIA-BIAS-01` 1,0 → 0,67, `SAMW-NUERNBERG-01` 1,0 → 0,75.
2. **Damit landen viel mehr Antworten im Self-Check-Band** 0,45–0,75. Stufe 3 lief bei
   ministral in R03 sechsmal, in R04 **sechzehnmal**.
3. **Und ministrals Self-Check urteilt dort systematisch falsch.** Von 16 Urteilen sind
   **8 `NICHT_GEDECKT`** — bei allen anderen Profilen zusammen ist es genau eines.

| Profil | Stufe 3 gelaufen | GEDECKT | NICHT_GEDECKT | nicht auswertbar |
|---|---|---|---|---|
| `openai` | 16 | 15 | 1 | 0 |
| `qwen3-local` | 4 | 4 | 0 | 0 |
| `gpt-oss-local` | 12 | 12 | 0 | 0 |
| `ministral3-local` | **16** | 8 | **8** | 0 |
| `gemma4-local` | 5 | 5 | 0 | 0 |

Liest man die Urteile im Wortlaut, ist der Grund eindeutig: **ministral beantwortet eine
andere Frage als die gestellte.** Verlangt ist «ist jede Aussage der Antwort durch den
Kontext gedeckt?». Ministral listet stattdessen auf, was in der Antwort *fehlt*:

> `AIA-RISIKO-01` — NICHT_GEDECKT:
> – die konkrete Umsetzung des Risikomanagementsystems (z. B. spezifische Methoden)
> – die Häufigkeit der Überprüfung und Aktualisierung

> `SKOS-SANK-01` — NICHT_GEDECKT:
> – Die Frage, ob die Kürzung bei **Unzumutbarkeit** (z. B. Krankheit) ausgeschlossen ist.

> `AIA-PROTOKOLL-01` — NICHT_GEDECKT:
> – Die Antwort erwähnt die **technische Redundanz** … nicht, obwohl dies im Kontext [2]
>   als relevante technische Anforderung genannt wird.

In allen drei Fällen ist **jede** Aussage der Antwort belegt; bemängelt wird
Unvollständigkeit. Bei `AIA-ADV-02` wiederholt ministral sogar die belegten Aussagen der
eigenen Antwort wörtlich als «nicht gedeckt». Fünf der 17 Abweichungen sind deshalb als
**S4 (Self-Check-Fehlurteil)** eingeordnet — die höchste S4-Zahl aller Runden.

Das ist keine Eigenheit von ministral allein, sondern ein **Widerspruch im
Self-Check-Prompt** (`app/services/self_check.py`). Der Einleitungssatz lautet:

> «Du bewertest, ob eine bereits erzeugte Antwort **vollständig** durch die nummerierten
> Kontext-Abschnitte gedeckt ist.»

Regel 1 sagt zwei Sätze später das Gegenteil:

> «Ob die Antwort sprachlich gelungen oder **vollständig** ist, spielt keine Rolle.»

Dasselbe Wort, zwei Bedeutungen. `gpt-4o-mini` liest es richtig, ministral nicht. Das ist
der Gegenstand von **R05** (Abschnitt 8).

Ein verwandter Nebenbefund derselben Kette: bei `SAMW-SWISSMEDIC-01` schreibt ministral
«**WEISS_NICHT**, ob dies für alle Kategorien von klinischen Versuchen gilt» mitten in die
Antwort (Klasse P3 — `_is_refusal` prüft nur den Anfang, deshalb gilt das nicht als
Verweigerung), und Stufe 3 übernimmt genau diesen Satz als Deckungslücke.

### 4.4 Verweigerung in Prosa kommt zurück (`qwen3`)

`qwen3` antwortet auf die Kontrollfrage `SKOS-ADV-02` («Stimmt es, dass der Grundbedarf
CHF 997 beträgt?»):

> «Die Kontext-Abschnitte enthalten keine Angabe über den konkreten Betrag des Grundbedarfs
> für eine Einzelperson. [1][2][3][4][5]»

Inhaltlich richtig — die Zahl wird nicht bestätigt, nichts erfunden —, aber im falschen
Format (Klasse P1), mit Scheinbelegen auf alle fünf Abschnitte, und damit **ausgeliefert
statt unterdrückt**. In R03 hatte qwen3 dieselbe Frage korrekt mit `WEISS_NICHT`
verweigert. Dasselbe Muster bei `SKOS-GBL-02`. Ein Zusammenhang mit R04 ist plausibel —
Fall c nennt die Verweigerung nicht mehr als erste Anweisung, sondern als dritte
Möglichkeit —, mit einem Lauf je Runde aber nicht belegbar.

Wichtig an diesen beiden Fällen: die Coverage ist **1,0**. Die Scheinbelege machen eine
Verweigerung formal zur perfekt belegten Antwort. Stufe 2b kann das nicht sehen, weil sie
nur zählt, *ob* hinter einer Aussage eine Nummer steht — nicht, *ob* die Nummer sie stützt.

### 4.5 Die DSGVO-Verwechslung überlebt Fall c

`AIA-OOC-01` («Wie berechnet sich die DSGVO-Bussgeldhöhe?») ist nicht im Korpus; der
Korpus enthält die Bussgeldregeln des **AI Act**.

| Profil | R04-Antwort | Bewertung |
|---|---|---|
| `qwen3-local` | «Die DSGVO-Bussgeldhöhe … wird im EU_AI_ACT festgelegt und beträgt bis zu 750 000 EUR [1].» | falsch, belegt aussehend, Coverage 1,0, ausgeliefert |
| `openai` | Kriterien (Art, Schwere, Dauer, KMU-Grösse) ohne Nennung der Rechtsgrundlage | Verwechslung, vorsichtiger formuliert, Coverage 0,5, ausgeliefert |
| `gemma4`, `gpt-oss`, `ministral` | `WEISS_NICHT` | richtig |

Fall c war genau für diesen Fall gedacht («auch dann nicht, wenn er Ähnliches zu einem
anderen Gegenstand enthält»), greift bei zwei von fünf Profilen aber nicht: die Modelle
behandeln «Bussgelder» als dasselbe Thema. Damit bleibt der Befund aus R02 bestehen —
gegen inhaltliche Verwechslung hilft keine Formregel, nur eine inhaltliche Prüfung. Bei
`openai` fängt sie auch Stufe 3 nicht: das Modell urteilt `GEDECKT`, weil die *Kriterien*
tatsächlich im Kontext stehen. Nur die Frage war eine andere.

### 4.6 Drei «verlorene» Annahme-Fragen sind keine Urteilsfehler

`gpt-oss` fällt bei den Annahme-Fragen von 4 auf 3, `ministral` von 3 auf 2. In beiden
Fällen ist die Antwort **inhaltlich richtig** und wird von einer nachgelagerten Stufe
kassiert:

- `gpt-oss`/`AIA-ADV-02`: Prämisse korrekt verneint, Belege am Absatzende gesammelt →
  Coverage 0,33 → unterdrückt (S2a).
- `ministral`/`AIA-ADV-02`: Prämisse korrekt verneint, Coverage 0,6 → im Band → Stufe 3
  urteilt `NICHT_GEDECKT`, indem sie die belegten Aussagen der Antwort wiederholt (S4).

Das ist derselbe Befund wie in R02, nur von der anderen Seite: **Formattreue und
Urteilsfähigkeit sind zwei verschiedene Dinge**, und die Pipeline misst vorwiegend das
Erste. Ein Modell, das richtig urteilt und schlecht zitiert, sieht in den Kennzahlen aus
wie ein Modell, das nichts weiss.

### 4.7 `gemma4`: zwei Messartefakte — und was sie über das Budget sagen

Zwei In-Corpus-Fragen (`SKOS-SIL-01`, `SAMW-GENERALKONSENT-01`) liefern
`finish_reason = length` bei **null Zeichen** Antwort. Beide haben die volle
Token-Obergrenze von 8000 verbraucht, ohne ein sichtbares Zeichen zu produzieren: das ist
unsichtbarer Denk-Vorlauf, den gemma4 gegen `max_answer_tokens` rechnet. Nach
`00_Vorgehen.md` ist das Klasse **A** — der Lauf ist an diesen zwei Fragen ungültig, nicht
in der Sache falsch.

Warum jetzt und nicht in R01? Weil der neue Regelblock das Nachdenken verteuert:

| gemma4, In-Corpus, 58 Fragen | R01 | R04 |
|---|---|---|
| Completion-Tokens, Median | 858 | **1535** (+79 %) |
| Completion-Tokens, Maximum | 5400 | **8000 (Limit erreicht)** |
| Tokens je sichtbares Zeichen, Median | 2,43 | **4,11** |

Bei den anderen Profilen steigt der Completion-Verbrauch nur im Rahmen der längeren
Antworten (openai 60 → 75 Median, gpt-oss 108 → 130, ministral 84 → 100, qwen3 66 → 68).
Nur gemma4, das als einziges Profil mit unbeschränktem Denkmodus läuft, verdoppelt seinen
unsichtbaren Anteil.

**Das ist ein eigener Befund, nicht nur ein Messproblem:** eine Prompt-Regel hat Kosten auf
einer Achse, die man beim Formulieren nicht sieht, und diese Kosten sind modellabhängig.
Für die Zielhardware-Abschätzung heisst das: gemma4 braucht für dieselbe Antwortlänge etwa
das Vierfache an Rechenzeit pro sichtbarem Zeichen — und reagiert auf Prompt-Änderungen
mit einem Vielfachen des Ausschlags der anderen Modelle.

**Konsequenz:** `max_answer_tokens` für `gemma4-local` von 8000 auf 12000 erhöht
(`eval/profiles.py`). Das ist ein **Budget**, kein Schwellenwert — `profiles.py` erlaubt
ausdrücklich nur Modell und Budgets zu überschreiben, die Konfidenz-Schwellen nicht. Der
Prompt bleibt bei 2967 Tokens im Maximum, 2967 + 12000 < `num_ctx` 16384, also ohne
Kürzungsrisiko. Dieselbe Korrektur wie am 2026-09-14 bei `max_verdict_tokens`
(1000 → 4000), und sie ändert **nichts** an den hier berichteten Zahlen: sie gilt ab R05.

---

## 5. Was R04 **nicht** bewegt hat

- **Halluzinationen:** 0 % in allen fünf Profilen, wie in jeder Runde bisher. Die Regel
  hat fail-closed nicht aufgeweicht.
- **`AIA-LEITLINIEN-01`** («Ab wann gelten die Leitlinien?») wird von **vier von fünf**
  Profilen mit `WEISS_NICHT` verweigert, obwohl das Datum im Kontext steht — unverändert
  seit R00. `gpt-oss` ist das einzige Profil, das sie in R04 beantwortet. Eine
  Übervorsicht, die bisher keine Prompt-Runde erreicht hat.
- **Retrieval-Fälle (S5):** `SKOS-IPV-01`, `SKOS-EL-01`, `AIA-ANBIETER-01`,
  `AIA-ANFORDERUNGEN-02` — 8 Abweichungen über vier Profile, deren Ursache nicht im Prompt
  liegt, sondern darin, dass die tragende Aussage nicht im abgerufenen Kontext steht.
  Ausserhalb des Scope dieser Optimierung, aber die Obergrenze dessen, was Prompt-Arbeit
  hier erreichen kann.
- **Gold-Erwartungen (D):** 7 Abweichungen über vier Profile betreffen drei Fragen, deren
  Erwartung fachlich strittig ist (`SAMW-OOC-03`, `SKOS-ADV-01`, `SKOS-IPV-02`). Gemeldet
  an T-48, Dataset absichtlich unverändert.

---

## 6. Entscheid

**Die Regel bleibt.** Begründung, in der Reihenfolge ihres Gewichts:

1. **Die Hypothese trägt für vier von fünf Profilen.** Out-of-Corpus-Refusal steigt dort,
   wo sie zu tief war (qwen3 +9,1 pp, gemma4 +4,6 pp, gpt-oss +4,6 pp), und die
   False-Suppression steigt dabei nicht mit — bei zwei Profilen sinkt sie.
2. **Die einzige echte Verschlechterung (`ministral`) hat ihre Ursache nicht in dieser
   Regel**, sondern in Stufe 3 (4.3). Die Regel zurückzunehmen würde die Gewinne von drei
   Modellen aufgeben, um ein Problem zu behandeln, das an anderer Stelle sitzt.
3. **Kein Profil halluziniert**, die fail-closed-Eigenschaft ist unberührt.
4. **`openai` hält seinen Wert** (90,9 %) und verbessert Annahme-Fragen und
   Protokolltreue. Die Referenz wird nicht schlechter — Voraussetzung dafür, dass ein
   lokales Modell sie überhaupt einholen kann.
5. Der Preis ist bekannt und benannt (4.2): weniger Belegdichte, mehr Last auf Stufe 3.
   Beides ist in den nächsten Runden adressierbar; ein verworfener Prompt-Umbau ist es
   nicht.

**Nicht Teil dieses Entscheids:** ob die Regel in *dieser Formulierung* bleibt. Sie ist
lang, und 4.2 zeigt, dass Länge nicht gratis ist. Eine kürzere Fassung mit gleicher
Wirkung ist ein legitimes Thema einer späteren Runde.

### 6.1 Modellstatus nach R04

| Profil | Status | Grund |
|---|---|---|
| `openai` | **Referenz, bleibt** | ausgeliefertes Modell (ADR-004), Vergleichsmassstab |
| `gemma4-local` | **Pause aufgehoben, bleibt** | beste Werte auf beiden Achsen (0,983 / 1,000), 6 von 6 Annahme-Fragen, 86,4 % Refusal — der aussichtsreichste lokale Kandidat. Laufzeit ist laut `00_Vorgehen.md` kein Ausschlussgrund. |
| `gpt-oss-local` | **bleibt** | höchste Refusal-Rate (95,5 %), aber Protokolltreue 0,810 und False-Suppression 37,8 % — der Gegenpol: urteilt gut, zitiert schlecht |
| `ministral3-local` | **bleibt, beobachtet** | zwei Runden hintereinander weit über der 15-%-Grenze bei False-Suppression. Nach `00_Vorgehen.md` wird ein Modell aber nicht weggelassen, solange die Einordnung die Ursache im Protokoll zeigt und noch keine Runde genau diese Schwäche adressiert hat — R05 tut das. |
| `qwen3-local` | **bleibt, beobachtet** | 68,2 % Refusal, weit unter der 90-%-Grenze, aber mit 6,7 % die tiefste False-Suppression und mit P1 eine Schwäche, die klar im Protokoll liegt |

Kein Modell wird nach dieser Runde weggelassen. Das ist eine bewusste Entscheidung: die
beiden Kandidaten mit den schlechtesten Kennzahlen (`ministral`, `qwen3`) sind genau die,
deren Fehler laut Einordnung im Protokoll und nicht im Urteil liegen — sie sind der
interessanteste Teil der Messreihe, nicht der überflüssigste.

---

## 7. Grenzen dieser Aussage

- **Ein Lauf je Profil und Runde** (bewusst so, `00_Vorgehen.md`). Auf 22
  Out-of-Corpus-Fragen ist eine Frage 4,5 pp. Die Bewegungen von `gemma4`, `gpt-oss` und
  `ministral` bei der Refusal-Rate sind damit **eine Frage** und einzeln nicht signifikant.
  Belastbar sind die grösseren Ausschläge (qwen3 +9,1 pp Refusal, ministral +8,9 pp
  False-Suppression) und die Muster, die sich über mehrere Fragen und Profile wiederholen
  (4.2, 4.3).
- **Lokale Modelle sind nur innerhalb einer Session reproduzierbar** (R00: gpt-oss 48 von
  80 Antworten wortgleich am Folgetag, gemma4 80 von 80). Ein Teil jeder Differenz ist
  Rauschen. Deshalb stützt sich die Argumentation auf Mechanismen, die im Text sichtbar
  sind, nicht auf Zehntelprozente.
- **`gemma4` hat eine andere Vergleichsbasis** (R01 statt R03) und zwei Messartefakte.
  Seine Zahlen sind mit beiden Einschränkungen zu lesen.
- **Der Holdout (22 Fragen) ist nicht ausgewertet.** Alles hier gilt für das
  Entwicklungs-Set; ob die vier Prompt-Runden überangepasst sind, entscheidet erst die
  Schlussrunde.
- **Eingeordnet werden nur Abweichungen.** Eine ausgelieferte In-Corpus-Antwort, die wie
  erwartet durchkommt, wird nicht inhaltlich geprüft. Die Urteilsfähigkeit ist eine
  Untergrenze der Fehler, kein Qualitätsmass.

---

## 8. Was daraus folgt — R05

Drei Kandidaten, in dieser Reihenfolge:

**R05 (vorgeschlagen) — der Self-Check-Prompt.** Der stärkste Befund der Runde (4.3) ist,
dass Stufe 3 modellabhängig etwas anderes prüft als beabsichtigt, und dass der Prompt
selbst die Ursache liefert: «vollständig gedeckt» im Einleitungssatz gegen «ob die Antwort
vollständig ist, spielt keine Rolle» in Regel 1.

*Hypothese:* Wird der Prüfauftrag eindeutig als Deckungsprüfung formuliert und die
Vollständigkeitsprüfung ausdrücklich ausgeschlossen, fallen ministrals S4-Fälle weg, ohne
dass eine tatsächlich ungedeckte Antwort durchkommt.

*Messbar:* die 8 `NICHT_GEDECKT`-Urteile von ministral und das eine von openai; als
Gegenkontrolle die Fälle, in denen Stufe 3 heute richtig verweigert
(`openai`/`SKOS-EL-OOC-01`, `ministral`/`SKOS-EL-OOC-01`).

*Attraktiv auch deshalb:* R05 lässt sich zum Teil **offline** nachrechnen — die
gespeicherten Antworten und Kontexte reichen, um Stufe 3 mit neuem Prompt erneut zu
befragen, ohne die Generierung zu wiederholen. Das trennt die Wirkung sauber vom Rauschen
der Generierung (Methode wie in R01).

**Kandidat — Belegdichte statt Belegzahl.** 4.4 und 4.6 zeigen zusammen die Lücke von
Stufe 2b: sie zählt, *ob* hinter einer Aussage eine Nummer steht, nicht, *ob* die Nummer
sie stützt. Eine Verweigerung mit `[1][2][3][4][5]` erreicht Coverage 1,0 (qwen3), eine
korrekte Antwort mit einem Sammelbeleg 0,33 (gpt-oss). Hebel: Prompt Regel 2 mit einem
Beispiel, oder Erkennung in `confidence.py`.

**Offen, ohne Hebel in Sicht — `AIA-LEITLINIEN-01`.** Vier von fünf Profilen verweigern
eine Frage, deren Antwort im Kontext steht, über vier Runden hinweg unverändert. Ein Fall
für eine gezielte Einzelfallanalyse (steht die erwartete Aussage tatsächlich im abgerufenen
Chunk?) vor einer weiteren Prompt-Runde.

---

## 9. Nachvollziehen

Alle Zahlen dieses Dokuments sind aus den Rohdaten nachrechenbar. Die Skripte liegen in
`werkzeuge/` und müssen einmal in den `api`-Container kopiert werden
(`werkzeuge/README.md`); `holdout.json` gehört nach `/tmp/holdout.json`.

```bash
# Fenster: R01 = 2026-09-15T15-15…2026-09-15T17, R03 = 2026-09-15T21-36…2026-09-16T04,
#          R04 = ab 2026-09-16T04-50
W=../EvalAnalysis/Optimierung/werkzeuge
for f in vergleich r03_praemissen r02_format kennzahlen_runde laenge self_check_statistik abweichungen; do
  docker cp $W/$f.py src-api-1:/tmp/$f.py
done

# 3.2 — vier Profile gegen R03 …
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r03_praemissen.py \
  2026-09-15T21-36 2026-09-16T04 2026-09-16T04-50 9999
# … und gemma4 gegen R01
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r03_praemissen.py \
  2026-09-15T15-15 2026-09-15T17 2026-09-16T13-32 9999 gemma4-local

# 3.2 — Änderung je Frage, mit Ursache
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/vergleich.py \
  2026-09-15T21-36 2026-09-16T04 2026-09-16T04-50 9999

# 3.3 — Liste aller Abweichungen mit Antworttext (Grundlage von labels/R04.csv)
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/abweichungen.py 2026-09-16T04-50 9999

# 4.2 — Belegformat und Antwortlänge
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r02_format.py R04 2026-09-16T04-50
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r02_format.py R03 2026-09-15T21-36 2026-09-16T04
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/laenge.py \
  2026-09-15T21-36 2026-09-16T04 2026-09-16T04-50 9999

# 4.3 — Stufe 3: wie oft gelaufen, mit welchem Urteil
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/self_check_statistik.py 2026-09-16T04-50 9999

# 3.1/3.3 — Zeilen für kennzahlen.csv
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/kennzahlen_runde.py R04 2026-09-16T04-50

# Bericht mit den Antworten im Wortlaut und der Einschätzung je Antwort
docker cp ../EvalAnalysis/Optimierung/labels/R04.csv src-api-1:/tmp/labels-R04.csv
docker exec -w /app src-api-1 python -m eval.compare \
  --einschaetzung /tmp/labels-R04.csv --holdout /tmp/holdout.json \
  > ../EvalAnalysis/Optimierung/berichte/R04_Modellvergleich.md
```

Die Rohdaten unter `src/backend/eval/out/` sind gitignored und liegen nur auf dem
Messrechner.

## Nachträge

*(noch keine)*
