# R02 — Zitierformat: erziehen oder tolerant lesen?

Zweite Optimierungsrunde. Dieses Dokument ist ohne weitere Dokumente lesbar; Vorgehen in
`00_Vorgehen.md`, Ausgangslage in `R00_Baseline.md` und `R01_Satzzerlegung.md`. Rohdaten und
Skripte: `kennzahlen.csv`, `berichte/R02a_Modellvergleich.md`, `werkzeuge/` (`r02_format.py`,
`r02b_offline.py`, `vergleich.py`).

## Worum es geht

LearnFlow beantwortet Fragen nur aus hochgeladenen Dokumenten und ist **fail-closed**. Nach der
Generierung prüft **Stufe 2 (Citation-Coverage)**, ob jede Aussage einen Beleg `[n]` auf einen
der fünf nummerierten Textabschnitte trägt; unter 50 % belegter Aussagen wird unterdrückt.

Nach R01 scheitern viele korrekte Antworten weiterhin am **Format** ihrer Belege:

- **Sammelbeleg** — ein Beleg für mehrere Sätze am Absatz- oder Listenende (gpt-4o-mini, gpt-oss);
- **fremdes Format** — `[1a]`, `[1.2b]`, `【1】`, die Stufe 2 nicht als Beleg erkennt (ministral, gpt-oss).

Zwei Wege, das zu beheben, und genau diese Gegenüberstellung ist die Lernfrage der Runde:

| Variante | Idee | Ort |
|---|---|---|
| **R02a — erziehen** | Das Modell wird im Prompt präziser angewiesen | Generierungs-Prompt, Regel 2 |
| **R02b — tolerant lesen** | Die Pipeline akzeptiert die Formate, die Modelle tatsächlich schreiben | Stufe 2, Referenzerkennung |

| Begriff | Bedeutung |
|---|---|
| **False-Suppression** | Anteil unterdrückter Fragen, deren Antwort im Korpus steht — tiefer ist besser |
| **Out-of-Corpus-Refusal** | Anteil korrekt verweigerter Fragen, deren Antwort nicht im Korpus steht — höher ist besser, Mindestwert 90 % |
| **Entwicklungs-Set (Dev)** | 58 der 80 Gold-Fragen; 22 weitere (Holdout) bleiben bis zur Schlussrunde unausgewertet |
| **Self-Check** | Stufe 3: dasselbe Modell prüft seine Antwort; läuft nur bei Konfidenz 0,45–0,75 |
| **unbelegte Aussagen** | Anteil der zählbaren Sätze und Listenpunkte ohne gültigen Beleg, über alle erzeugten Antworten |

Gemessen: `openai` (Referenz gpt-4o-mini), `qwen3-local`, `gpt-oss-local`, `ministral3-local`.
`gemma4-local` ist für R02 und R03 pausiert (Entscheid 2026-09-15).

## Kernaussage

> **Erziehen wirkt — tolerant lesen wird danach überflüssig. Aber Formtreue ist nicht
> Belegtheit.** Ein präziserer Prompt senkt die unbelegten Aussagen bei allen Modellen (gpt-oss
> 56 % → 41 %, ministral 36 % → 21 %, gpt-4o-mini 41 % → 28 %) und die False-Suppression bei
> gpt-oss von 14 auf 8 Fragen. Nach dem Prompt bringt tolerantes Lesen nur noch eine Frage — und
> zwar ausgerechnet eine inhaltlich falsche Antwort. Gleichzeitig zeigt die Runde die Kehrseite:
> Wer brav jeden Satz belegt, belegt auch falsche Sätze. qwen3 liefert eine Verwechslung
> (DSGVO-Bussen mit AI-Act-Kriterien beantwortet) mit Coverage 1,0 aus — Stufe 2 hatte bisher
> nebenbei als inhaltlicher Filter gewirkt, weil halluzinierte Antworten schlecht belegt waren.

| Profil | unbelegte Aussagen R01 → R02a | fremdes Format | False-Suppression Dev | Out-of-Corpus Dev | tolerantes Lesen danach (R02b) |
|---|---|---|---|---|---|
| `openai` | 41 % → **28 %** | 0 % → 0 % | 10 → **8** | 16 → 16 | ±0 |
| `qwen3-local` | 14 % → 7 % | 0 % → 0 % | 1 → 0 | 11 → **9** ⚠️ | ±0 |
| `gpt-oss-local` | 56 % → **41 %** | 5 % → **0 %** | 14 → **8** | 14 → 14 | ±0 |
| `ministral3-local` | 36 % → **21 %** | 24 % → **3 %** | 10 → 9 | 16 → 16 | −1 (falsche Antwort) |

## 1. Hypothesen

> **R02a:** Präzisiert man Regel 2 — Beleg hinter jedem Satz und Listenpunkt, nur die Nummer —,
> sinken Sammelbelege und fremde Formate bei gpt-4o-mini, gpt-oss und ministral; die
> False-Suppression sinkt, Out-of-Corpus-Refusal und Halluzinationsrate bleiben.
>
> **R02b:** Liest Stufe 2 `【1】`, `[1a]`, `[1.2b]`, `[1(3a)]` als `[1]`, sinkt die
> False-Suppression vor allem bei ministral, ohne dass eine unbelegte Aussage durchkommt.

## 2. Änderungen

**R02a — Prompt, Regel 2** (`app/services/generation.py`, Commit `02eefb7`, Test in
`tests/test_generation.py`):

| vorher | nachher |
|---|---|
| Belege jede Aussage mit der Nummer des Abschnitts in eckigen Klammern, direkt hinter der Aussage, zum Beispiel [1] oder [2][3]. | … zum Beispiel [1] oder [2][3]. **Das gilt für jeden Satz und jeden Listenpunkt einzeln: Sammle Belege nicht am Ende eines Absatzes oder einer Liste. Schreibe nur die Nummer, ohne Buchstaben, Unterpunkte oder andere Klammern.** |

**R02b — tolerantes Lesen**, nur offline gemessen, nicht im Code: `【n】`, `[na]`, `[n.m…]`,
`[n(…)]` werden vor Stufe 2 zu `[n]`. Die Nummer wird wie bisher gegen 1..5 geprüft; eine
erfundene Nummer bleibt erfunden, Buchstaben allein (`[f]`) bleiben kein Beleg.

## 3. Messung

| Messung | Was |
|---|---|
| **Format** | Anteil unbelegter Aussagen, Antworten mit fremdem Format oder Sammelbeleg — direkt an den erzeugten Texten, unabhängig von Unterdrückungen (`r02_format.py`) |
| **R02a live** | Prompt-Änderung, alle vier Profile auf Commit `02eefb7` |
| **R02b offline** | tolerantes Lesen auf den gespeicherten Antworten — einmal auf R01-, einmal auf R02a-Antworten (`r02b_offline.py`); Kontrolle: die strikte Lesart reproduziert jeweils alle gespeicherten Entscheide |

**Gültigkeit R02a:** alle Aufrufe `finish_reason = stop`, keine leeren Antworten.

**Zuordnung von Änderungen:** Anders als in R01 ändert R02a die Antworten selbst. Jede
geänderte Frage geht deshalb auf «Antworttext» zurück — Prompt-Wirkung und Rauschen lassen
sich pro Frage nicht trennen (lokale Modelle sind nur innerhalb einer Sitzung reproduzierbar,
R01). Belastbar sind darum die **Format-Kennzahlen über alle Antworten**, weil sie die Richtung
zeigen, die die Änderung verlangt; einzelne Unterdrückungen sind als Beispiele zu lesen.

## 4. Ergebnisse

### 4.1 Format der Antworten (Dev, alle Antworten mit Text)

| Profil | unbelegte Aussagen | fremdes Format | Antworten mit Sammelbeleg |
|---|---|---|---|
| `openai` | 41 % → 28 % | 0 % → 0 % | 46 % → 47 % |
| `qwen3-local` | 14 % → 7 % | 0 % → 0 % | 11 % → 4 % |
| `gpt-oss-local` | 56 % → 41 % | 5 % → 0 % | 42 % → 37 % |
| `ministral3-local` | 36 % → 21 % | 24 % → 3 % | 24 % → 14 % |

Bei gpt-4o-mini sinkt der Anteil unbelegter Sätze deutlich, der Anteil der Antworten mit
*mindestens einem* Sammelbeleg aber nicht: Das Modell belegt mehr Sätze einzeln, fällt aber in
fast jeder zweiten Antwort noch irgendwo ins alte Muster zurück.

### 4.2 Kennzahlen R02a

Alle 80 Fragen:

| Profil | Out-of-Corpus-Refusal R01 → R02a | False-Suppression R01 → R02a | Halluzination (Pool) |
|---|---|---|---|
| `openai` | 95,5 % → 95,5 % | 33,3 % → **28,9 %** | 0 % (37) |
| `qwen3-local` | 68,2 % → **59,1 %** | 6,7 % → 4,4 % | 0 % (50) |
| `gpt-oss-local` | 90,9 % → 90,9 % | 44,4 % → **28,9 %** | 0 % (37) |
| `ministral3-local` | 100 % → 100 % | 33,3 % → 31,1 % | 0 % (34) |

Entwicklungs-Set:

| Profil | False-Suppression | Out-of-Corpus verweigert | Abweichungen | Self-Check gelaufen | wortgleich zu R01 |
|---|---|---|---|---|---|
| `openai` | 10 → 8 | 16 → 16 | 14 → 12 | 15 → 12 | 50 / 80 |
| `qwen3-local` | 1 → 0 | 11 → 9 | 9 → 10 | 8 → 6 | 39 / 80 |
| `gpt-oss-local` | 14 → 8 | 14 → 14 | 20 → 15 | 9 → 10 | 31 / 80 |
| `ministral3-local` | 10 → 9 | 16 → 16 | 16 → 14 | 10 → 7 | 37 / 80 |

### 4.3 Tolerantes Lesen (R02b, offline, Dev)

| Profil | auf R01-Antworten | auf R02a-Antworten |
|---|---|---|
| `openai` | 10 → 10 | 8 → 8 |
| `qwen3-local` | 1 → 1 | 0 → 0 |
| `gpt-oss-local` | 14 → 13 (+1 Self-Check offen) | 8 → 8 |
| `ministral3-local` | 10 → **6** (+4 Self-Check offen) | 9 → 8 |

Ohne Prompt-Änderung wäre tolerantes Lesen für ministral ein grosser Gewinn. Nach der
Prompt-Änderung bleibt eine einzige Frage — `AIA-ANFORDERUNGEN-02`, deren Antwort den
«Bevollmächtigten» statt der gefragten Dokumentationsintegration nennt, also inhaltlich falsch
ist. Sie käme mit Coverage 0,88 ins Band «hoch» und würde **ohne Self-Check ausgeliefert**.

## 5. Befunde

### 5.1 Formtreue macht falsche Antworten belegbar

`AIA-OOC-01` («Wie berechnet sich die DSGVO-Bussgeldhöhe?» — nicht im Korpus):

| Runde | qwen3-Antwort | Ergebnis |
|---|---|---|
| R01 | erfundene DSGVO-Prozentsätze, kaum belegt, dazu «WEISS_NICHT.» am Ende | Coverage 0,33 → unterdrückt |
| R02a | «… wird auf der Grundlage der Art, der Schwere und der Dauer des Verstoßes … berechnet [3]. Die Höhe der Geldbuße wird zudem an die Größe des Anbieters angepasst … [3].» — die Bussgeldregeln des **AI Act**, als DSGVO ausgegeben | Coverage 1,0, Band «hoch», kein Self-Check → **ausgeliefert** |

Die Antwort ist eine Verwechslung (Klasse F1), jeder Satz stimmt mit dem zitierten Abschnitt
überein — nur nicht mit der Frage. Stufe 2 prüft Form, und die Form ist jetzt tadellos. Die
Halluzinationsprüfung schlägt nicht an, weil das zitierte Dokument im Korpus liegt.

**Folge:** Solange halluzinierte Antworten auch schlecht belegt waren, hat Stufe 2 nebenbei
Inhalte gefiltert. Je besser ein Modell das Belegprotokoll befolgt, desto mehr hängt die
inhaltliche Sicherheit am Self-Check — und der läuft seit R01 seltener und nie im Band «hoch».

### 5.2 Neue Fehlerform: Dokument-Nummern statt Abschnitts-Nummern

Die Anweisung «nur die Nummer, ohne Buchstaben» verschiebt bei ministral den Fehler statt ihn zu
beseitigen: Statt `[1a]` zitiert es jetzt die Erwägungsgründe des EU AI Act — `[13]`, `[38]`,
`[65]` —, also Nummern *aus* dem Dokument statt der Nummer des Abschnitts. Stufe 2 wertet das
korrekt als erfundene Referenz (`citation_invalid`; zwei Antworten im Dev-Set, eine im Holdout). gpt-oss zeigte dasselbe
Muster schon in R01 (`[13]`). «Nummer des Abschnitts» ist für diese Modelle mehrdeutig, sobald
der Abschnitt selbst nummerierte Absätze enthält.

### 5.3 qwen3 verweigert schlechter

Out-of-Corpus-Refusal 68,2 % → 59,1 %: neben `AIA-OOC-01` (5.1) antwortet qwen3 bei `AIA-OOC-02`
(«Ist ChatGPT als hochriskant klassifiziert?») mit einer Prosa-Verweigerung plus belegten
Allgemeinaussagen — Self-Check `GEDECKT`, ausgeliefert. Ob der längere Prompt qwen3 vom
`WEISS_NICHT` weglenkt oder Rauschen die Ursache ist, lässt sich mit einem Lauf nicht trennen;
die Richtung passt zur Änderung. qwen3 lag schon vorher unter der 90-%-Grenze.

### 5.4 Methodischer Hinweis

Beim Prüfen der ungültigen Referenzen (5.2) wurde die Antwort einer **Holdout-Frage**
(`AIA-DATEN-01`) angezeigt. Ausgewertet wurde nur das Referenzformat; die Frage wird nicht
eingeordnet, und das Muster ist über zwei Dev-Fragen belegt.

## 6. Entscheid

| Frage | Vorschlag | Begründung |
|---|---|---|
| R02a (Prompt) behalten? | **ja** | Unbelegte Aussagen bei allen Modellen tiefer; False-Suppression der Referenz 10 → 8 und von gpt-oss 14 → 8; Out-of-Corpus-Refusal der Referenz unverändert, Halluzinationsrate 0 %. Die Prompt-Änderung betrifft das ausgelieferte System → Nachtrag in ADR-007/008 nach Bestätigung |
| R02b (tolerantes Lesen) übernehmen? | **nein** | Nach R02a Wirkung −1, und diese eine Frage ist eine inhaltlich falsche Antwort, die ohne Self-Check ausgeliefert würde. Tolerantes Lesen hätte ohne Prompt-Änderung geholfen — erziehen ist hier die bessere Stellschraube |
| Modelle | keine Änderung | qwen3 bleibt unter der 90-%-Grenze; ob es wegfällt, entscheidet eine Runde, die Verweigerungen adressiert (R04) |
| Offene Risiken | an R03 / Kalibrierung | Formtreue schwächt Stufe 2 als inhaltlichen Filter (5.1); «Nummer des Abschnitts» ist mehrdeutig (5.2); Self-Check-Band nach R01 (T-57) |

**Nächste Runde (Vorschlag):** R03 wie geplant — falsche Prämissen und Ja/Nein-Schlüsse (R00:
18 Fälle S1). Die Befunde 5.1 und 5.2 legen zusätzlich nahe, die Referenzanweisung
eindeutig zu machen («die Nummer in eckigen Klammern **vor** dem Abschnitt, nicht Nummern aus
dem Text»); das wäre eine eigene, kleine Runde.

## Nachträge

*(noch keine)*
