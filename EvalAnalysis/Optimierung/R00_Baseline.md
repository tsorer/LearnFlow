# R00 — Baseline

Ausgangslage der Optimierung: fünf Sprachmodelle in der unveränderten Pipeline. Dieses
Dokument ist ohne weitere Dokumente lesbar; Rohdaten zum Nachrechnen: `kennzahlen.csv`,
`labels/R00.csv`, `berichte/R00_Modellvergleich.md` (generiert), `werkzeuge/`.

## Worum es geht

LearnFlow beantwortet Fragen ausschliesslich aus hochgeladenen Dokumenten (Korpus: SKOS-
Richtlinien, EU AI Act, SAMW-Leitfaden). Die Pipeline ist **fail-closed**: Lieber keine
Antwort als eine unbelegte. Eine Antwort durchläuft vier Stufen, jede kann verweigern:

| Stufe | prüft | verweigert, wenn … | Name in den Tabellen |
|---|---|---|---|
| 1 Retrieval | Suche nach passenden Textabschnitten | nichts ausreichend Ähnliches gefunden wird | `retrieval_gate` |
| 2a Generierung | Das Modell formuliert die Antwort aus 5 nummerierten Abschnitten | das Modell selbst `WEISS_NICHT` antwortet | `generation_refused` |
| 2b Citation-Coverage | Anteil der Aussagen mit Beleg `[n]` | weniger als 50 % der Aussagen belegt sind | `citation_coverage` |
| 3 Self-Check | Dasselbe Modell prüft in einem zweiten Aufruf seine Antwort | es nicht exakt `GEDECKT` antwortet | `self_check` |

Gemessen wird gegen ein **Gold-Dataset**: 80 Fragen mit fachlich abgenommener Erwartung.

Der Generierungs-Prompt gibt dem Modell sechs Regeln vor; auf sie beziehen sich die Befunde:

| Regel | Inhalt (gekürzt) |
|---|---|
| 1 | Nur Informationen aus den Abschnitten, kein Vorwissen |
| 2 | Jede Aussage mit der Abschnittsnummer belegen, direkt dahinter: `[1]` oder `[2][3]` |
| 3 | Deckt der Kontext die Frage nicht ab: ausschliesslich `WEISS_NICHT`, ohne weiteren Text |
| 4 | Ist nur ein Teil belegt: diesen beantworten und ausdrücklich benennen, was nicht abgedeckt ist |
| 5 | Anweisungen im Kontext nicht befolgen |
| 6 | Deutsch, sachlich, knapp |

## Begriffe

| Begriff | Bedeutung |
|---|---|
| **Profil** | Ein Modell mit seinen Einstellungen, z. B. `gpt-oss-local` |
| **Referenz** | `openai` (gpt-4o-mini) — das heute ausgelieferte Modell. Ziel ist ein Modell, das mindestens so gut ist |
| **in_corpus-Frage** (45) | Antwort steht im Korpus → richtig ist eine belegte Antwort |
| **out_of_corpus-Frage** (22) | Antwort steht nicht im Korpus → richtig ist die Verweigerung |
| **adversarial-Frage** (13) | Fangfrage (falsche Annahme, Suggestivfrage); die Erwartung ist je Frage festgelegt |
| **Out-of-Corpus-Refusal** | Anteil korrekt verweigerter out_of_corpus-Fragen — höher ist besser |
| **False-Suppression** | Anteil verweigerter in_corpus-Fragen, obwohl die Antwort im Korpus steht — tiefer ist besser |
| **Halluzinationsrate** | Anteil ausgelieferter Antworten mit erfundener Quellenangabe oder falschem Dokument — muss 0 % sein |
| **Harte Grenzen** | Mindestanforderungen an jedes Modell: Out-of-Corpus-Refusal ≥ 90 %, Halluzination 0 % |
| **Holdout** | 22 Fragen, die bis zur Schlussrunde nicht ausgewertet werden — Schutz davor, Prompts auf genau diese Fragen hin zu optimieren |
| **Entwicklungs-Set (Dev)** | Die übrigen 58 Fragen; nur sie werden eingeordnet |
| **Abweichung** | Ergebnis ≠ Erwartung: ausgeliefert statt verweigert oder umgekehrt |
| **Urteilsfähigkeit** | Anteil der Dev-Fragen, bei denen das Modell inhaltlich richtig entschieden hat — auch wenn das Format nicht stimmte |
| **Protokolltreue** | Anteil der Dev-Fragen, bei denen das Modell im geforderten Format geantwortet hat (`WEISS_NICHT`, Beleg `[n]` hinter jeder Aussage) |

## Kernaussage

> **Die False-Suppression ist überwiegend ein Formatproblem, kein Urteilsproblem.**
> Von 59 Unterdrückungen beantwortbarer Fragen im Entwicklungs-Set (alle Modelle) waren
> 30 Antworten inhaltlich richtig — gescheitert an der Art, wie belegt wurde (22),
> oder an der Satzzerlegung der Pipeline (8). Echte Übervorsicht (S1) macht 18 aus. Jedes Modell scheitert dabei auf seine
> eigene Art: gpt-4o-mini und gpt-oss sammeln Belege am Absatzende, ministral erfindet
> Unterverweise wie `[1a]`, gpt-oss schreibt `【1】`, qwen3 verweigert in Prosa.

| Profil | Urteilsfähigkeit | Protokolltreue | Abweichungen (Dev) | davon Format/Pipeline (S2) |
|---|---|---|---|---|
| `openai` gpt-4o-mini | 89,7 % | 91,4 % | 14 | 5 |
| `qwen3-local` | 93,1 % | 94,8 % | 9 | 0 |
| `gemma4-local` | 98,3 % | 98,3 % | 10 | 3 |
| `gpt-oss-local` | 86,2 % | 81,0 % | 22 | 12 |
| `ministral3-local` | 86,2 % | 86,2 % | 19 | 10 |

**Grenze beider Achsen:** Eingeordnet werden nur Abweichungen. Eine ausgelieferte Antwort,
die wie erwartet durchkommt, wird nicht inhaltlich geprüft. qwen3 liefert am meisten aus
und wird damit am wenigsten geprüft — seine hohen Werte sind vorsichtig zu lesen.

## 1. Messgrundlage

| | |
|---|---|
| Git-Stand | `08c0d19` + Profile `gpt-oss-local`, `ministral3-local` (uncommitted) |
| Schwellen | Seed-Defaults, in allen Läufen identisch |
| Retrieval | für alle Profile Chunk für Chunk identisch (geprüft über alle 22 Out-of-Corpus-Fragen) |
| Testhardware | RTX 3070 Laptop 8 GB, 32 GB RAM, i7-11800H (lokale Modelle über Ollama) |

| Profil | Modell | Lauf Out-of-Corpus | Lauf In-Corpus |
|---|---|---|---|
| `openai` | gpt-4o-mini | 2026-09-14T21-24-38Z | 2026-09-14T21-22-57Z |
| `qwen3-local` | qwen3:8b (`think: false`) | 2026-09-14T21-33-46Z | 2026-09-14T21-25-06Z |
| `gemma4-local` | gemma4:26b (`max_verdict_tokens` 4000) | 2026-09-15T06-03-35Z | 2026-09-15T04-52-33Z |
| `gpt-oss-local` | gpt-oss:20b (`think: low`) | 2026-09-14T18-12-16Z | 2026-09-14T18-00-05Z |
| `ministral3-local` | ministral-3:14b | 2026-09-14T18-45-03Z | 2026-09-14T18-15-48Z |

### Gültigkeit

Alle Aufrufe `finish_reason = stop`, keine leeren Antworten, keine Fehler.

Der erste gemma4-Lauf vom 14.09. war **ungültig**: Zwei Self-Check-Aufrufe brauchten das
Budget von 1000 Tokens vollständig für unsichtbares Denken und lieferten ein leeres Urteil
(`finish_reason = length`), das die Pipeline vorsichtshalber als Verweigerung wertete
(`SAMW-SUBSIDIARITAET-01`, `AIA-ADV-04`). Mit `max_verdict_tokens` 4000 wiederholt: Diese
beiden Antworten werden jetzt ausgeliefert, alle übrigen 78 sind wortgleich. Die Baseline
verwendet den gültigen Wiederholungslauf. Beide Fragen liegen im Holdout — Einordnung und
Entwicklungs-Set sind unverändert.

### Reproduzierbarkeit

gpt-oss und ministral wurden am selben Tag zweimal gemessen: Ergebnis je Frage in allen
80 Fällen identisch (gpt-oss auch wortgleich, ministral 76 von 80 wortgleich). Bei gemma4
unterscheiden sich die zwei Läufe nur in den beiden Fragen, deren Budget geändert wurde. Die
Referenz ist es nicht: Out-of-Corpus-Refusal 90,9 % in diesem Lauf gegenüber 91–95,5 %
in früheren, False-Suppression 31,1 % gegenüber 33–38 %.

**Einschränkung (Nachtrag 2026-09-15):** Die Reproduzierbarkeit der lokalen Modelle gilt nur
*innerhalb einer Sitzung*. Im R01-Lauf einen Tag später — gleicher Prompt, gleicher Kontext,
gleiche Parameter, gleiche Modell-ID und Ollama-Version — waren nur noch 48 von 80
gpt-oss-Antworten wortgleich (qwen3 72, ministral 75). Die Ursache ist nicht belegt;
wahrscheinlich hängt der Rechenweg bei Temperatur 0 vom Zustand der Grafikkarte ab.

## 2. Holdout

22 von 80 Fragen, festgelegt vor jeder Auswertung und ab jetzt unverändert. Regel: je
Schicht (Kategorie × Korpus) die Fragen nach `sha256(id)` sortieren und die ersten
`round(0,3 × n)` nehmen — reproduzierbar ohne Zufallsgenerator.

| Kategorie | Holdout |
|---|---|
| in_corpus (12) | `AIA-ANFORDERUNGEN-01`, `AIA-DATEN-01`, `AIA-KMU-01`, `AIA-RUECKRUF-01`, `SAMW-EMANUEL-01`, `SAMW-QUALI-ERHEBUNG-01`, `SAMW-RICHTLINIEN-01`, `SAMW-SUBSIDIARITAET-01`, `SKOS-ALI-01`, `SKOS-KV-02`, `SKOS-KV-AUF-01`, `SKOS-PRINZ-03` |
| out_of_corpus (6) | `AIA-OOC-03`, `AIA-OOC-07`, `SAMW-OOC-02`, `SAMW-OOC-06`, `SKOS-ALI-OOC-01`, `SKOS-OOC-03` |
| adversarial (4) | `AIA-ADV-04`, `AIA-ADV-05`, `SAMW-ADV-03`, `SKOS-ADV-EL-01` |

Entwicklungs-Set: 58 Fragen (33 in_corpus, 16 out_of_corpus, 9 adversarial).

**Einschränkung:** `AIA-OOC-07` (deutsches KI-Umsetzungsgesetz) und `SAMW-OOC-06` wurden
in einer früheren Messreihe (10.09.) bereits im Wortlaut besprochen, bevor der Holdout bestand. Sie
bleiben trotzdem im Holdout — sie herauszunehmen hiesse, die Regel nach Kenntnis der
Ergebnisse anzupassen.

## 3. Kennzahlen

Alle 80 Fragen, wie `make eval` sie misst:

| Profil | Out-of-Corpus-Refusal | Halluzination (Pool) | False-Suppression | Adversarial-Refusal | Kontext-Recall |
|---|---|---|---|---|---|
| `openai` | 90,9 % | 0 % (36) | 31,1 % | 1/2 | 0,78 |
| `qwen3-local` | **68,2 %** | 0 % (49) | **6,7 %** | 1/2 | 0,78 |
| `gemma4-local` | **81,8 %** | 0 % (49) | 11,1 % | 1/2 | 0,78 |
| `gpt-oss-local` | 90,9 % | 0 % (27) | **48,9 %** | 2/2 | 0,78 |
| `ministral3-local` | **100 %** | 0 % (29) | 40,0 % | 2/2 | 0,78 |

Entwicklungs-Set (Grundlage der Einordnung):

| Profil | Out-of-Corpus-Refusal | False-Suppression | … ohne Pipeline-Fehler S2c/S2d |
|---|---|---|---|
| `openai` | 15/16 | 9/33 | 9/33 |
| `qwen3-local` | 11/16 | 1/33 | 1/33 |
| `gemma4-local` | 12/16 | 4/33 | 2/33 |
| `gpt-oss-local` | 14/16 | 15/33 | 13/33 |
| `ministral3-local` | 16/16 | 13/33 | 10/33 |

## 4. Einordnung der Abweichungen

74 Abweichungen im Entwicklungs-Set, jede einzeln begründet in `labels/R00.csv`.
Vorklassifikation und Begründungen: Claude (KI-Assistent), anhand von Antworttext,
Kontext-Abschnitten und Referenzantwort des Gold-Datasets; zu bestätigen durch die
Projektverantwortlichen.

Die Kennzahlen sagen nur, *ob* verweigert wurde. Die Klassen sagen, *warum* — und ob das
Modell dabei inhaltlich richtig lag:

| Klasse | Situation | Modell inhaltlich | Format |
|---|---|---|---|
| **S1** Übervorsicht | beantwortbare Frage mit `WEISS_NICHT` verweigert (auch: falsche Annahme verweigert statt korrigiert) | falsch | eingehalten |
| **S2a** Sammelbeleg | Antwort richtig, aber ein Beleg für mehrere Aussagen am Ende → Coverage zu tief | richtig | Verstoss (Modell) |
| **S2b** Fremdes Zitatformat | Antwort richtig, Beleg als `【1】`, `[1a]`, `[1.2]` — von der Pipeline nicht erkannt | richtig | Verstoss (Modell) |
| **S2c** Segmentierung | Antwort richtig und korrekt belegt, die Pipeline zerlegt sie falsch in Sätze | richtig | eingehalten — **Fehler der Pipeline** |
| **S2d** Lückensatz | ein vom Prompt verlangter Satz «… nicht abgedeckt» zählt als unbelegt | richtig | eingehalten — **Widerspruch in der Pipeline** |
| **S3** Echte Deckungslücke | Antwort enthielt unbelegte oder falsche Aussagen | falsch | — Verweigerung korrekt |
| **S4** Self-Check-Fehlurteil | korrekte Antwort, Selbstprüfung urteilt «nicht gedeckt» | falsch (als Prüfer) | eingehalten |
| **S5** Retrieval | die nötige Textstelle war gar nicht unter den Abschnitten | — | — ausserhalb des Modells |
| **P1** Prosa-Verweigerung | «steht nicht im Kontext» geschrieben statt `WEISS_NICHT` → ausgeliefert | richtig | Verstoss |
| **P2** Teilantwort mit Lücke | belegter Teil plus ausdrücklich benannte Lücke, wie der Prompt es erlaubt | richtig | eingehalten |
| **P3** Sentinel im Fliesstext | `WEISS_NICHT` mitten in einer Antwort (nur Nebenklasse) | — | Verstoss |
| **F1** Verwechslung | belegte Aussage zu einem anderen Gegenstand als gefragt | falsch | eingehalten |
| **D** Gold-Erwartung strittig | die Erwartung des Gold-Datasets ist fachlich falsch oder widersprüchlich | richtig | eingehalten |

| Klasse | openai | qwen3 | gemma4 | gpt-oss | ministral | Σ |
|---|---|---|---|---|---|---|
| S1 Übervorsicht | 6 | 1 | 1 | 5 | 5 | 18 |
| S2a Sammelbeleg | 5 | – | 1 | 7 | – | 13 |
| S2b Fremdes Zitatformat | – | – | – | 3 | 6 | 9 |
| S2c Segmentierung *(Pipeline)* | – | – | 2 | 2 | 3 | 7 |
| S2d Lückensatz *(Pipeline)* | – | – | – | – | 1 | 1 |
| S3 Echte Deckungslücke | – | 2 | – | – | – | 2 |
| S4 Self-Check-Fehlurteil | – | – | – | 1 | 1 | 2 |
| S5 Retrieval | – | – | – | 2 | 2 | 4 |
| P1 Prosa-Verweigerung | – | 2 | – | – | – | 2 |
| P2 Teilantwort mit Lücke | 1 | 1 | 3 | – | – | 5 |
| F1 Verwechslung | – | 1 | – | 1 | – | 2 |
| D Gold-Erwartung strittig | 2 | 2 | 3 | 1 | 1 | 9 |
| **Σ** | 14 | 9 | 10 | 22 | 19 | 74 |

Nebenklasse P3 (Sentinel im Fliesstext): qwen3 1×, ministral 2×.

## 5. Befunde

### 5.1 Das Gold-Dataset hat einen Fehler — und er erklärt die schwankende Referenz

`SAMW-OOC-03` («Innert welcher Frist müssen SUSAR der Ethikkommission gemeldet werden?»)
ist als Out-of-Corpus markiert, Notiz: «Konkrete Meldefristen sind nicht im Leitfaden
enthalten». Der Leitfaden enthält sie aber — PDF-Seite 83, Tabelle der Meldefristen:
«SUSAR, vgl. Art. 41 KlinV — Innerhalb von 7 Tagen / Innerhalb von 15 Tagen». Das Retrieval
liefert genau diesen Chunk als `[1]`.

- Vier von fünf Modellen beantworten die Frage richtig und zählen dafür als Fehler.
- Es ist dieselbe Frage, an der die Referenz über mehrere Läufe zwischen 91 % und 95,5 %
  pendelt: gpt-4o-mini liefert die Antwort mal aus, mal nicht, weil die Coverage genau um
  die Schwelle von 0,5 schwankt. Die Schwankung der Referenz hängt also an einer falsch
  erwarteten Frage.

Zwei weitere Fälle sind strittig: `SKOS-ADV-01` erwartet eine Antwort, die Referenzantwort
erlaubt aber ausdrücklich «Weiss ich nicht»; `SKOS-IPV-02` erwartet Verweigerung, obwohl
qwen3 und gemma4 nur die laut Notiz belegbare Aussage machen.

**Folge:** Die drei Fragen gehen zur fachlichen Prüfung an die Person, die das
Gold-Dataset abgenommen hat (Issue T-48). In dieser Optimierung wird das Dataset nicht
geändert.

### 5.2 Stufe 2 unterdrückt korrekt belegte Antworten

Acht Antworten waren korrekt und korrekt belegt — und wurden trotzdem als unbelegt
unterdrückt, weil `check_citations` die Antwort falsch in Segmente zerlegt. Nachgerechnet
mit der Pipeline-Funktion selbst:

| Muster | Beispiel | Wirkung |
|---|---|---|
| Ordinalzahl als Satzende | «… ab dem vollendeten 14. ⏐ Lebensjahr als Jugendliche. [4]» | Beleg landet im Rest unter 4 Wörtern, Aussage gilt als unbelegt |
| Abkürzung in Klammer | «(z. ⏐ B. Kinder, Ehepartner) [4]» | `(z. B.` wird nicht erkannt |
| Kurze Listenpunkte | «* Anonymisiert [1]» | unter `MIN_SEGMENT_WORDS = 4` übersprungen; gezählt wird nur die unbelegte Einleitung → Coverage 0,0 |
| Einleitung mit Doppelpunkt | «… umfasst die folgenden Positionen:» | zählt in jeder Aufzählung als unbelegte Aussage |
| Sehr kurze Antwort | «NEIN [1].» | kein zählbares Segment → Coverage 0,0 |
| Lückensatz nach Regel 4 | «Nicht abgedeckt: Konkrete Definitionen …» | der Prompt verlangt den Satz, Stufe 2 zählt ihn als unbelegt |

Der letzte Punkt ist ein Widerspruch in der Pipeline selbst: Der Generierungs-Prompt
verlangt, Lücken zu benennen (Regel 4), der Self-Check erklärt solche Sätze für gedeckt
(Regel 3) — nur Stufe 2 bestraft sie.

Eine frühere Messreihe (10.09.) hatte gezeigt, dass Coverage Kürze belohnt: «Innerhalb von
7 Tagen [1].» erreicht 1,0 und umgeht damit den Self-Check. Zusammen ergibt sich ein
zweiseitiges Bild: Ein kurzer Satz ab 4 Wörtern erreicht leicht 1,0, eine Aufzählung aus
kurzen, einzeln belegten Punkten erreicht 0,0.

### 5.3 Jedes Modell belegt anders

| Modell | typisches Muster | Beispiel |
|---|---|---|
| gpt-4o-mini | Sammelbeleg am Absatz- oder Listenende (S2a) | 9 korrekte Listenpunkte, `[1]` nur hinter dem letzten |
| gpt-oss:20b | Sammelbeleg (7×), vollbreite Klammern `【1】`, Buchstaben `[f][g]` | `i. Übriges【1】` |
| ministral-3:14b | Unterverweise auf Absätze im Chunk (6×) | `[1a]`, `[1.2b]`, `[1(3a)]` |
| gemma4:26b | meist konform; Teilantworten mit benannter Lücke (P2) | «Eine Mindestversicherungssumme wird im Kontext nicht genannt.» |
| qwen3:8b | Verweigerung in Prosa statt `WEISS_NICHT` (P1) | «wird nicht im Kontext-Abschnitt direkt erläutert [1][2][3][4][5]» |

ministrals Unterverweise sind inhaltlich präziser als der geforderte Beleg — das Modell
verweist auf den Buchstaben im Gesetzesabsatz. Die Pipeline kennt dieses Format nicht
und wertet die präziseste Antwort als unbelegt. Das ist die Leitthese in einem Fall:
nicht schlechter, sondern anders.

### 5.4 Übervorsicht hängt an der Frage, nicht am Modell

Die 18 S1-Fälle konzentrieren sich auf wenige Fragen, die mehrere Modelle gleichzeitig
verweigern:

| Frage | verweigert von | Muster |
|---|---|---|
| `SKOS-IPV-01` «Muss … die IPV beanspruchen?» | openai, gpt-oss, ministral | Ja/Nein-Frage, Antwort nur als Schlussfolgerung aus dem Kontext |
| `SKOS-EL-01` «Gehen EL der Sozialhilfe vor?» | openai, gpt-oss, ministral | Ja/Nein-Frage mit Schlussfolgerung |
| `AIA-LEITLINIEN-01` «Bis wann …?» | openai, gemma4, ministral (gpt-oss: Self-Check) | Datum steht im Kontext |
| `SAMW-ADV-01` «Auf welcher Seite steht das Verbot …?» | openai, qwen3, gpt-oss, ministral | falsche Prämisse |
| `SAMW-ADV-02` «Wie lauten alle fünf Prinzipien?» | openai, gpt-oss, ministral | falsche Prämisse (es sind drei) |

Der Prompt kennt nur zwei Wege: antworten (Regel 1/2/4) oder `WEISS_NICHT` (Regel 3). Für
eine Frage mit **falscher Annahme** gibt es keine Regel — die Modelle wählen die sichere
Verweigerung, obwohl der Kontext die Annahme widerlegt.

### 5.5 Echte inhaltliche Fehler sind selten — und werden teils gefangen

- **F1** `SKOS-EL-OOC-01` (qwen3, gpt-oss): ein Sonderfall (AHV-Vorbezug) wird als
  Berechnungsweise der Ergänzungsleistungen ausgegeben. Ausgeliefert, Self-Check `GEDECKT`.
  gemma4 macht aus demselben Kontext eine korrekte Teilantwort mit benannter Lücke.
- **S3** `SKOS-IPV-01` (qwen3): «Nein, muss nicht beanspruchen» — inhaltlich falsch, vom
  Self-Check korrekt gestoppt.
- **S4** `AIA-LEITLINIEN-01` (gpt-oss): korrekte, belegte Antwort, Self-Check urteilt
  `NICHT_GEDECKT`.

### 5.6 Protokoll-Nebenbefund: Sentinel im Fliesstext

ministral schreibt `WEISS_NICHT, ob weitere Aspekte …` mitten in eine Antwort, qwen3 hängt
`WEISS_NICHT` ans Ende. `_is_refusal` prüft nur den Anfang (`startswith`). In R00 wurden
alle drei Antworten aus anderen Gründen unterdrückt — hätten sie Stufe 2 und 3 passiert,
stünde das Sentinel im Text vor dem Nutzer.

## 6. Laufzeiten auf der Testhardware

Die lokalen Modelle laufen bewusst auf minimaler Hardware. Was darauf nicht läuft, wird nicht
evaluiert — so landet kein Modell in der Auswahl, das nur mit teurer Hardware betreibbar
wäre. Die Zeiten sind **kein Ausschlusskriterium**, sondern Grundlage, um die nötige
Zielhardware und die Betriebskosten abzuschätzen.

| Profil | Generierung Median / p95 | Self-Check Median / p95 | LLM-Zeit total | Tokens/s effektiv¹ |
|---|---|---|---|---|
| `openai` (Cloud) | 0,8 s / 2,1 s | 0,7 s / 1,6 s | 1:37 min | – |
| `qwen3-local` | 6,0 s / 13,9 s | 3,9 s / 9,7 s | 10:45 min | 7,8 |
| `gpt-oss-local` | 7,8 s / 15,6 s | 8,4 s / 14,7 s | 14:35 min | 10,6 |
| `ministral3-local` | 11,9 s / 54,2 s | 5,4 s / 80,7 s | 32:48 min | 3,5 |
| `gemma4-local` | 40,1 s / 137,0 s | 36,0 s / 55,0 s | 87:52 min | 17,7² |

¹ Completion-Tokens geteilt durch Aufrufdauer, inklusive Prompt-Verarbeitung — ein
Vergleichswert, keine Generierungsgeschwindigkeit.
² Hoch, weil gemma4 viele unsichtbare Denk-Tokens erzeugt (bis 5400 je Aufruf).

Kein lokales Modell erreicht auf der Testhardware p95 ≤ 10 s (Vorgabe für die Produktion).
Kein lokales Modell passt mit 16K-Kontext vollständig in die 8 GB VRAM: qwen3 läuft zu 20 %
auf der CPU, gpt-oss zu 58 %, ministral zu 50 %; gemma4 (18 GB) ist am langsamsten. qwen3 und
gpt-oss liegen nahe an der Vorgabe; ministral und gemma4 bräuchten für die Produktion
deutlich mehr VRAM.

## 7. Eignung — Stand R00

| Profil | Stufe 2 (harte Grenzen) | Stufe 3 (vs. Referenz) | Entscheid |
|---|---|---|---|
| `ministral3-local` | erfüllt | Refusal besser; False-Suppression schlechter (40 % vs. 31 %), zu einem Drittel Format | **bleibt** |
| `gpt-oss-local` | erfüllt | Refusal gleich; False-Suppression schlechter (49 %), überwiegend Format | **bleibt** |
| `gemma4-local` | Refusal 81,8 % < 90 % | alle vier Out-of-Corpus-Abweichungen im Dev-Set sind richtige Urteile (3× P2, 1× Gold-Fehler) | **bleibt** — Ursache liegt im Protokoll |
| `qwen3-local` | Refusal 68,2 % < 90 % | Abweichungen überwiegend Protokoll (P1, P2) und Gold | **bleibt** bis eine Runde P1 adressiert hat |
| `openai` | erfüllt | Referenz | **bleibt** (Referenz) |

Kein Modell wird weggelassen. Die Regel dafür: Ein Modell fällt erst weg, wenn es zweimal
hintereinander eine harte Grenze verfehlt **und** die Ursache nicht im Antwortformat liegt.
Bei gemma4 und qwen3 liegt sie im Format — und genau das sollen die nächsten Runden über
den Prompt angehen.

## 8. Folgerungen für die nächsten Runden

Nach Wirkung sortiert, gemessen an den Fällen im Entwicklungs-Set:

| Vorschlag | Hebel | adressiert | Fälle | Messbar |
|---|---|---|---|---|
| **R01 Stufe-2-Segmentierung** | `confidence.py`: Ordinalzahlen, «(z. B.», kurze belegte Listenpunkte, Einleitungen, Lückensätze | S2c, S2d | 8 | offline aus gespeicherten Antworten nachrechenbar, danach ein Lauf |
| **R02 Zitierformat im Prompt** | Regel 2 mit Beispiel für Listen, Verbot von Unterverweisen | S2a, S2b | 22 | Lauf aller Profile |
| **R03 Falsche Prämisse und Ja/Nein-Schlüsse** | neue Regel im Generierungs-Prompt | S1 | bis 18 | Lauf aller Profile |
| **R04 Regel 3 vs. Regel 4** | Verweigerung vs. Teilantwort schärfen | P1, P2, P3 | 9 | Lauf aller Profile |

R01 zuerst, weil es modellunabhängig ist und jede spätere Prompt-Runde sonst gegen einen
Messfehler optimiert. R01 ändert Produktionscode (`confidence.py`) und braucht deshalb einen
eigenen PR mit Tests; die Fail-closed-Richtung darf dabei nicht kippen — eine wirklich
unbelegte Aussage muss unbelegt bleiben.

**Vorbedingungen**
1. Fachliche Prüfung von `SAMW-OOC-03`, `SKOS-ADV-01`, `SKOS-IPV-02` (5.1).
2. Bestätigung der Einordnung in `labels/R00.csv` durch die Projektverantwortlichen.
## Nachträge

- **2026-09-15:** gemma4-Wiederholungslauf mit `max_verdict_tokens` 4000 übernommen
  (Abschnitt 1, Gültigkeit). Gesamtkennzahlen gemma4: False-Suppression 13,3 % → 11,1 %,
  Halluzinations-Pool 47 → 49, jeweils durch die zwei Holdout-Fragen. Entwicklungs-Set,
  Einordnung und Eignung unverändert.
- **2026-09-15:** Reproduzierbarkeit der lokalen Modelle eingeschränkt auf eine Sitzung
  (Abschnitt 1, Reproduzierbarkeit), belegt durch den R01-Lauf.
