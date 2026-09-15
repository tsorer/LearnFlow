# R01 — Satzzerlegung in Stufe 2

Erste Optimierungsrunde. Dieses Dokument ist ohne weitere Dokumente lesbar; Vorgehen und
Begriffe ausführlich in `00_Vorgehen.md` und `R00_Baseline.md`, Rohdaten und Skripte in
`kennzahlen.csv` und `werkzeuge/` (`r01_offline.py`, `r01_segmente.py`, `r01_vergleich.py`).

## Worum es geht

LearnFlow beantwortet Fragen nur aus hochgeladenen Dokumenten und ist **fail-closed**: lieber
keine Antwort als eine unbelegte. Nach der Generierung prüft **Stufe 2 (Citation-Coverage)**,
ob jede Aussage der Antwort einen Beleg `[n]` auf einen der fünf Textabschnitte trägt. Liegt
der Anteil belegter Aussagen unter 50 %, wird die Antwort unterdrückt.

Dazu zerlegt Stufe 2 die Antwort mechanisch in **Segmente** (Sätze und Listenpunkte) — die
**Satzzerlegung**. Sie entscheidet, was als Aussage zählt. Zerlegt sie falsch, wird eine
korrekt belegte Antwort als unbelegt unterdrückt; klebt sie falsch zusammen, trägt der Beleg
eines Satzes einen unbelegten mit (fail-open). Der zweite Fehler darf nie passieren.

| Begriff | Bedeutung |
|---|---|
| **False-Suppression** | Anteil unterdrückter Fragen, deren Antwort im Korpus steht — tiefer ist besser |
| **Out-of-Corpus-Refusal** | Anteil korrekt verweigerter Fragen, deren Antwort nicht im Korpus steht — höher ist besser |
| **Entwicklungs-Set (Dev)** | 58 der 80 Gold-Fragen; 22 weitere (Holdout) bleiben bis zur Schlussrunde unausgewertet |
| **Self-Check** | Stufe 3: dasselbe Modell prüft in einem zweiten Aufruf seine Antwort — läuft nur bei Konfidenz zwischen 0,45 und 0,75 |
| **Konfidenz** | 0,5 × Retrieval-Score + 0,5 × Coverage |

## Kernaussage

> **Ein Teil der False-Suppression war ein Messfehler der Pipeline, nicht der Modelle.**
> Nach der Korrektur der Satzzerlegung sinkt sie genau wie offline vorhergesagt — gemma4
> 4 → 2, ministral 13 → 10 Fragen im Entwicklungs-Set —, ohne dass eine unbelegte Aussage
> neu durchkommt und ohne Einbusse beim Out-of-Corpus-Refusal. Der Preis: Korrekt gemessene
> Coverage hebt die Konfidenz, und der Self-Check läuft seltener (live 70 → 53 Mal). Und die
> Runde zeigt eine Grenze der Methode: gpt-oss antwortete bei identischer Eingabe einen Tag
> später auf 32 von 80 Fragen anders, gemma4 auf keine.

| Profil | False-Suppression Dev R00 → R01 | davon durch R01 (offline, rauschfrei) | Out-of-Corpus Dev | Self-Check gelaufen Dev | wortgleich zu R00 |
|---|---|---|---|---|---|
| `openai` | 9 → 10 | 0 | 15 → 16 | 20 → 15 | 65 / 80 |
| `qwen3-local` | 1 → 1 | 0 | 11 → 11 | 12 → 8 | 72 / 80 |
| `gemma4-local` | 4 → **2** | −2 | 12 → 12 | 15 → 11 | 80 / 80 |
| `gpt-oss-local` | 15 → 14 | −2 | 14 → 14 | 13 → 9 | 48 / 80 |
| `ministral3-local` | 13 → **10** | −3 | 16 → 16 | 10 → 10 | 75 / 80 |

«davon durch R01»: Änderungen, die bei gleichem Antworttext allein die neue Satzzerlegung
bewirkt (Messung C, gemma4 identisch mit A). ministral: offline −5, zwei dieser Antworten lehnte
der Self-Check live ab — netto −3. Siehe Abschnitt 3.

## 1. Hypothese

> Stufe 2 zerlegt korrekt belegte Antworten falsch in Sätze und unterdrückt sie deshalb
> (R00, Befund 5.2: 8 Fälle). Wird die Zerlegung korrigiert, sinkt die False-Suppression
> bei gemma4, gpt-oss und ministral, **ohne dass eine unbelegte Aussage neu als belegt gilt**.

**Erwarteter Effekt** (vor dem Live-Lauf festgehalten): False-Suppression im Dev-Set bei
ministral, gpt-oss und gemma4 um je 1–3 Fragen tiefer, bei openai und qwen3 kaum Änderung;
Out-of-Corpus-Refusal unverändert; Halluzinationsrate unverändert 0 %.

## 2. Änderung

Eine Stellschraube — die Satzzerlegung in `app/services/confidence.py` —, vier Regeln.
Jede ist mit dem R00-Fall getestet, den sie repariert, und mit einem Gegenbeispiel, das
weiterhin unterdrückt werden muss (`tests/test_confidence.py`, 14 neue Tests).

| # | Regel | Fall aus R00 | Gegenbeispiel (bleibt getrennt / unbelegt) |
|---|---|---|---|
| 1 | Ordinalzahl vor Monat oder «Lebensjahr», «Altersjahr», «Jahrhundert» beendet keinen Satz | «… des 14. ⏐ Lebensjahres [4].» | «gemäss Abs. 2. Weitere Pflichten folgen [1].» |
| 2 | Buchstabenpaar auch nach Klammer oder Anführungszeichen | «(z. ⏐ B. Kinder, Ehepartner) [4]» | «Anhang A. Weitere Pflichten [1].» |
| 3 | Segment mit `:` am Ende und ohne Beleg ist Struktur | «… umfasst folgende Positionen:» | unbelegte Listenpunkte darunter zählen weiter als unbelegt |
| 4 | Listenpunkt mit gültigem Beleg zählt, gleich welcher Länge | «* Anonymisiert [1]» | «NEIN [1].» ausserhalb einer Liste bleibt ohne zählbares Segment |

**Bewusst nicht geändert:** Lückensätze nach Prompt-Regel 4 («Nicht abgedeckt: …»), fremde
Zitatformate (`【1】`, `[1a]`), sehr kurze Antworten — Begründung in ADR-008, Nachtrag
2026-09-15, und `Docs/09_RAG-Pipeline-Referenz.md`, Abschnitt 5.6.

Code-Stand der Messung: `0dedbaa`. Keine Änderung an Prompt, Schwellen, Retrieval, Modellen.

## 3. Messung

Drei Messungen, weil der Live-Lauf allein die Wirkung nicht isoliert (siehe 3.3):

| Messung | Was | Wozu |
|---|---|---|
| **A — offline auf R00-Antworten** | gespeicherte R00-Antworten mit alter und neuer Zerlegung neu bewertet | reine Wirkung der Regeln, vor der Umsetzung |
| **B — live** | alle Profile neu gemessen (`make eval`) | Wirkung inkl. Self-Check-Urteilen und Rauschen |
| **C — offline auf R01-Antworten** | die im Live-Lauf entstandenen Antworten mit alter und neuer Zerlegung | reine Wirkung auf die tatsächlich erzeugten Antworten |

**Kontrolle:** Die alte Zerlegung reproduziert alle gespeicherten R00-Entscheide exakt, die
neue alle R01-Entscheide — die Nachrechnung rechnet also nachweislich wie die Pipeline.
Offline nicht nachrechenbar ist nur das Urteil eines Self-Checks, der neu laufen müsste
(«Self-Check offen»).

**Gültigkeit Live-Lauf:** alle Aufrufe `finish_reason = stop`, keine leeren Antworten.
gemma4 brach beim ersten Start mit `CUDA out of memory` ab (ministral noch nicht vollständig
entladen) und wurde auf demselben Code-Stand neu gestartet.

**Einordnung:** Anders als in R00 wird nicht jede Abweichung neu klassifiziert — R01 ändert die
Generierung nicht. Eingeordnet sind die Fälle, die sich ändern (Abschnitte 5 und 6); die
Klassen aus R00 gelten für die übrigen weiter, soweit der Antworttext gleich blieb.

### 3.1 Wirkung der Regeln (A und C, Dev-Set)

False-Suppression, alt → neu:

| Profil | A (R00-Antworten) | C (R01-Antworten) |
|---|---|---|
| `openai` | 9/33 → 9/33 | 10/33 → 10/33 |
| `qwen3-local` | 1/33 → 1/33 | 1/33 → 1/33 |
| `gemma4-local` | 4/33 → **2/33** | 4/33 → **2/33** (Antworten identisch mit R00) |
| `gpt-oss-local` | 15/33 → **11/33** (+1 Self-Check offen) | 16/33 → **14/33** |
| `ministral3-local` | 13/33 → **8/33** (+2 Self-Check offen) | 12/33 → **10/33** |

Out-of-Corpus-Refusal bleibt in beiden Nachrechnungen für alle Profile gleich.

Beitrag je Regel (A, Dev-Set, Fragen weniger unterdrückt, wenn nur diese Regel aktiv ist):

| Regel | gemma4 | gpt-oss | ministral |
|---|---|---|---|
| 1 Ordinalzahl | 1 | 2 | 0 |
| 2 Klammer-Abkürzung | 0 | 1 | 2 |
| 3 Einleitung | 0 | 0 | 2 |
| 4 kurzer Listenpunkt | 1 | 1 | 2 |

Regeln können dieselbe Antwort betreffen oder erst zusammen wirken; die Summe je Modell muss
deshalb nicht der Gesamtwirkung entsprechen (ministral: Summe 6, gesamt 5).

### 3.2 Live-Ergebnis (B)

Alle 80 Fragen:

| Profil | Out-of-Corpus-Refusal R00 → R01 | False-Suppression R00 → R01 | Halluzination (Pool) |
|---|---|---|---|
| `openai` | 90,9 % → 95,5 % | 31,1 % → 33,3 % | 0 % (35) |
| `qwen3-local` | 68,2 % → 68,2 % | 6,7 % → 6,7 % | 0 % (50) |
| `gemma4-local` | 81,8 % → 81,8 % | 11,1 % → 6,7 % | 0 % (51) |
| `gpt-oss-local` | 90,9 % → 90,9 % | 48,9 % → 44,4 % | 0 % (30) |
| `ministral3-local` | 100 % → 100 % | 40,0 % → 33,3 % | 0 % (32) |

Entwicklungs-Set, mit Ursache jeder geänderten Frage:

| Profil | False-Suppression | Out-of-Corpus verweigert | geändert durch Coverage (R01) | geändert durch Antworttext (Rauschen) |
|---|---|---|---|---|
| `openai` | 9 → 10 | 15 → 16 | 5 | 7 |
| `qwen3-local` | 1 → 1 | 11 → 11 | 3 | 2 |
| `gemma4-local` | 4 → **2** | 12 → 12 | 20 | 0 |
| `gpt-oss-local` | 15 → 14 | 14 → 14 | 5 | 13 |
| `ministral3-local` | 13 → 10 | 16 → 16 | 16 | 3 |

Die Prognose aus A traf bei den Modellen ohne Rauschen exakt: gemma4 (Antworten wortgleich) 4 → 2
wie vorhergesagt; ministral 8 plus die zwei offenen Fälle, die der Self-Check live ablehnte,
ergibt 10. Bei gpt-oss überlagert das Rauschen die Wirkung (13 von 18 Änderungen durch neuen
Antworttext); Messung C zeigt dort die reine Wirkung: 16 → 14.

### 3.3 Rauschen: lokale Modelle sind nur innerhalb einer Sitzung reproduzierbar

Gleicher Prompt, gleicher Kontext (Chunk für Chunk), gleiche Parameter, gleiche Modell-ID und
Ollama-Version wie in R00 — und trotzdem andere Antworten:

| Profil | wortgleich zu R00 |
|---|---|
| `openai` | 65 / 80 |
| `qwen3-local` | 72 / 80 |
| `gpt-oss-local` | **48 / 80** |
| `ministral3-local` | 75 / 80 |
| `gemma4-local` | **80 / 80** |

In R00 waren zwei gpt-oss-Läufe am selben Abend in allen 80 Fällen wortgleich; gemma4 ist es
auch über zwei Tage. Die Reproduzierbarkeit hängt also vom Modell ab. Die Ursache ist nicht
belegt; denkbar ist, dass der Rechenweg bei Temperatur 0 je nach Modellarchitektur und
Aufteilung auf GPU und CPU nicht bitgenau gleich bleibt. **Folge für die Methode:**
Ein Live-Vergleich zweier Runden misst Änderung *und* Rauschen. Die Wirkung einer Änderung
wird deshalb, wo möglich, zusätzlich offline auf identischen Antworten gemessen (A, C).

## 4. Nebeneffekt: Der Self-Check läuft seltener

Korrekt gemessene Coverage ist höher, damit steigt die Konfidenz, und mehr Antworten landen
im Band «hoch» (≥ 0,75), in dem der Self-Check nicht läuft:

| Profil | Self-Check läuft (A) | Band «hoch» ohne Prüfung (A) | Self-Check gelaufen live, Dev |
|---|---|---|---|
| `openai` | 20 → 17 | 10 → 13 | 20 → 15 |
| `qwen3-local` | 12 → 9 | 33 → 36 | 12 → 8 |
| `gemma4-local` | 15 → 11 | 25 → 31 | 15 → 11 |
| `gpt-oss-local` | 13 → 9 | 11 → 18 | 13 → 9 |
| `ministral3-local` | 10 → 10 | 13 → 18 | 10 → 10 |

Beispiel: ministral `SKOS-WOHN-01` wurde in R00 vom Self-Check abgelehnt; in R01 steigt die
Konfidenz über 0,75, die Antwort wird ohne Prüfung ausgeliefert.

Die Bandgrenzen (0,45 / 0,75) wurden gegen die fehlerhafte, zu tiefe Messung gewählt.
R01 macht Stufe 2 genauer — und schwächt dadurch Stufe 3. In dieser Runde bewusst nicht
korrigiert (Schwellen sind nicht im Scope); als Befund an die Kalibrierung (T-57).

Gleichzeitig zeigt der Live-Lauf, dass der Self-Check wirkt, wo er läuft: Bei ministral
lehnte er drei Antworten ab, die dank R01 Stufe 2 neu passierten — darunter die inhaltlich
falsche `AIA-ANBIETER-01` und die Out-of-Corpus-Frage `SKOS-EL-OOC-01`.

## 5. Prüfung der Fehlerrichtung

Jede Antwort, deren Entscheid oder Band sich durch R01 ändert (A: 28 Antworten), wurde Segment
für Segment verglichen (`werkzeuge/r01_segmente.py`). In allen Fällen wird ein zuvor falsch
getrennter Satz wieder zusammengefügt, eine Einleitung übersprungen oder ein belegter
Listenpunkt gezählt. **Keine unbelegte Sachaussage zählt neu als belegt.**

**Restrisiko:** Regel 3 überspringt jede Zeile mit Doppelpunkt am Ende. Eine Zwischenüberschrift
mit Sachaussage — ministral: «### Grundversorgende SIL (Übernahme zwingend, wenn …):» — wird
dadurch nicht mehr als unbelegt gezählt. Beobachtet einmal, ohne Einfluss auf den Entscheid.

## 6. Weitere Befunde aus dem Live-Lauf

- **Falsche Antwort ausgeliefert, nicht durch R01.** gpt-oss `AIA-ANFORDERUNGEN-02` nennt den
  «Bevollmächtigten» statt der gefragten Integration in bestehende Dokumentation. Coverage
  genau 0,5, Self-Check `GEDECKT` — ausgeliefert. Mit der alten Zerlegung wäre dieselbe Antwort
  ebenfalls durchgekommen; neu ist der Antworttext (Rauschen). Die Halluzinationsprüfung
  schlägt nicht an, weil das richtige Dokument zitiert wird — die bekannte Grenze aller
  automatischen Messungen hier.
- **Erfundene Referenz korrekt gestoppt.** gpt-oss `AIA-TRANSPARENZ-01` zitiert `[13]` bei fünf
  Abschnitten → `citation_invalid`. Nebenbei: «sufficiently transparent» mitten im deutschen
  Text.
- **Referenz schwankt ebenfalls.** openai `SAMW-OOC-03` (Gold-Fehler, siehe R00) wurde diesmal
  verweigert, `AIA-ANFORDERUNGEN-02` neu vom Self-Check gestoppt — beides Antworttext, nicht R01.

## 7. Entscheid

| Frage | Entscheid | Begründung |
|---|---|---|
| Änderung behalten? | **ja** | Hypothese bestätigt: Wirkung wie vorhergesagt, keine unbelegte Aussage neu als belegt (Abschnitt 5), Out-of-Corpus-Refusal und Halluzinationsrate unverändert |
| Modelle weglassen / aufnehmen? | keines weggelassen · **gemma4 pausiert** für R02 und R03, Wiederaufnahme in R04 (Entscheid Projektverantwortliche, 2026-09-15) | R01 ändert an der Eignung nichts. gemma4 belegt mit 86 min LLM-Zeit rund 60 % jeder Runde und hat als Produktivmodell auf Grund von Laufzeit und Hardwarebedarf kaum Chancen; es bleibt aber das protokolltreueste Modell und zentral für die Frage Regel 3 vs. Regel 4. Pausieren statt Weglassen, weil es für R04 gebraucht wird |
| Befund an Kalibrierung (T-57) | Self-Check-Band prüfen | Die Bandgrenzen wurden gegen die zu tiefe Coverage-Messung gewählt; nach R01 läuft Stufe 3 deutlich seltener (Abschnitt 4) |
| Nächste Runde | **R02 Zitierformat** | Nach R01 ist das Belegformat der grösste verbleibende Formatfehler (R00: Sammelbeleg S2a 13×, fremdes Format S2b 9×, vor allem gpt-oss, ministral, openai). Vorschlag: bewusst zwei Varianten messen — Format per Prompt erzwingen vs. Pipeline liest `[1a]`, `【1】` tolerant |

## Nachträge

*(noch keine)*
