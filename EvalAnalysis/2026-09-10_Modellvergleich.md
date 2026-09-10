# Eval-Messreihe — Modellvergleich

Erzeugt mit `python -m eval.compare` aus den Läufen unten. Gemessen wird die
Out-of-Corpus-Refusal-Rate des Gold-Datasets (ADR-009); das Gate von 90 %
gilt nur für das ausgelieferte Profil.

## Läufe

| Profil | Modell | Refusal-Rate | Fragen | Gate | Lauf | Git-SHA |
|---|---|---|---|---|---|---|
| `openai` | gpt-4o-mini | **95,5 %** | 22 | ja | 2026-09-10T14-03-37Z | fe011b2 |
| `qwen3-local` | ollama_chat/qwen3:8b | **68,2 %** | 22 | nein | 2026-09-10T14-04-21Z | fe011b2 |
| `gemma4-local` | ollama_chat/gemma4:26b | **81,8 %** | 22 | nein | 2026-09-10T14-06-47Z | fe011b2 |

## Wirksame Schwellen

Über alle Läufe identisch (Seed-Defaults), die Raten sind vergleichbar:

| Parameter | Wert |
|---|---|
| `confidence_threshold_high` | 0.75 |
| `confidence_threshold_medium` | 0.45 |
| `context_top_n` | 5 |
| `min_citation_coverage` | 0.5 |
| `min_retrieval_confidence` | 0.4 |
| `retrieval_top_k` | 20 |
| `rrf_k` | 60 |
| `self_check_band_high` | 0.75 |
| `self_check_band_low` | 0.45 |
| `similarity_threshold` | 0.35 |

## Pro Frage

`*` markiert eine Abweichung von der Erwartung des Gold-Datasets.

| Frage | erwartet | `openai` | `qwen3-local` | `gemma4-local` |
|---|---|---|---|---|
| `SKOS-GBL-02` | Verweigerung | Generierung | Antwort `*` | Generierung |
| `SKOS-OOC-01` | Verweigerung | Generierung | Antwort `*` | Generierung |
| `SKOS-OOC-02` | Verweigerung | Generierung | Generierung | Generierung |
| `SKOS-OOC-03` | Verweigerung | Generierung | Generierung | Generierung |
| `SKOS-OOC-04` | Verweigerung | Generierung | Generierung | Generierung |
| `SKOS-IPV-OOC-01` | Verweigerung | Generierung | Antwort `*` | Antwort `*` |
| `SKOS-ALI-OOC-01` | Verweigerung | Generierung | Generierung | Generierung |
| `SKOS-EL-OOC-01` | Verweigerung | Generierung | Antwort `*` | Antwort `*` |
| `AIA-OOC-01` | Verweigerung | Generierung | Coverage | Generierung |
| `AIA-OOC-02` | Verweigerung | Generierung | Generierung | Generierung |
| `AIA-OOC-03` | Verweigerung | Generierung | Generierung | Generierung |
| `AIA-OOC-04` | Verweigerung | Generierung | Generierung | Generierung |
| `AIA-OOC-05` | Verweigerung | Generierung | Generierung | Generierung |
| `AIA-OOC-06` | Verweigerung | Generierung | Generierung | Generierung |
| `AIA-OOC-07` | Verweigerung | Antwort `*` | Antwort `*` | Generierung |
| `SAMW-OOC-01` | Verweigerung | Generierung | Generierung | Generierung |
| `SAMW-OOC-02` | Verweigerung | Generierung | Generierung | Generierung |
| `SAMW-OOC-03` | Verweigerung | Coverage | Antwort `*` | Antwort `*` |
| `SAMW-OOC-04` | Verweigerung | Generierung | Generierung | Antwort `*` |
| `SAMW-OOC-05` | Verweigerung | Generierung | Generierung | Generierung |
| `SAMW-OOC-06` | Verweigerung | Generierung | Antwort `*` | Generierung |
| `SAMW-OOC-07` | Verweigerung | Generierung | Generierung | Generierung |

## Woran es scheitert

Wo die Pipeline unterdrückt hat — die Verteilung sagt mehr als die Rate:
eine Verweigerung durch das Modell selbst (`Generierung`) ist ein anderes
Verhalten als eine, die erst eine nachgelagerte Schwelle erzwingt.

| Profil | Verteilung |
|---|---|
| `openai` | Generierung 20, Antwort 1, Coverage 1 |
| `qwen3-local` | Generierung 14, Antwort 7, Coverage 1 |
| `gemma4-local` | Generierung 18, Antwort 4 |

## LLM-Aufrufe

`finish_reason` ist die Kontrolle gegen Messartefakte: ein Lauf mit `length`
oder mit leeren Antworten misst das Token-Budget, nicht das Modell. Beides
muss 0 sein, damit die Raten oben etwas bedeuten.

| Profil | Aufrufe | finish_reason | leer | Fehler | Σ Dauer | max | median |
|---|---|---|---|---|---|---|---|
| `openai` | 23 | `stop` 23 | 0 | 0 | 26 s | 3,0 s | 1,1 s |
| `qwen3-local` | 27 | `stop` 27 | 0 | 0 | 132 s | 18,2 s | 2,8 s |
| `gemma4-local` | 25 | `stop` 25 | 0 | 0 | 1134 s | 112,7 s | 39,4 s |

Token-Verbrauch, gemessen am Anbieter:

| Profil | Prompt max | Prompt median | Completion max |
|---|---|---|---|
| `openai` | 2322 | 2113 | 204 |
| `qwen3-local` | 3046 | 2639 | 222 |
| `gemma4-local` | 2835 | 2267 | 1964 |

## Self-Check (ADR-008, Stufe 3)

Die Stufe läuft nur im Konfidenz-Grenzband. Wie oft sie überhaupt greift,
ist selbst ein Befund: eine kurze, vollständig belegte Antwort landet im
Band «hoch» und wird gar nicht mehr geprüft.

| Profil | gelaufen | Urteile |
|---|---|---|
| `openai` | 1 von 22 | GEDECKT 1 |
| `qwen3-local` | 5 von 22 | GEDECKT 5 |
| `gemma4-local` | 3 von 22 | GEDECKT 3 |

## Abweichungen im Wortlaut

Jede Antwort, die entgegen der Erwartung ausgeliefert wurde. Die Einordnung
muss ein Mensch vornehmen — die Kennzahlen oben unterscheiden nicht zwischen
einer erfundenen Aussage und einer korrekten Verweigerung im Fliesstext.

### `openai` — gpt-4o-mini

**`AIA-OOC-07`** — Welche Strafen sieht das deutsche KI-Umsetzungsgesetz für Verstösse vor?

> Das deutsche KI-Umsetzungsgesetz sieht folgende Strafen für Verstöße vor:
>
> 1. Geldbußen von bis zu 3 % des gesamten weltweiten Jahresumsatzes im vorangegangenen Geschäftsjahr oder 15.000.000 EUR, je nachdem, welcher Betrag höher ist, für Anbieter von KI-Modellen mit allgemeinem Verwendungszweck, wenn sie vorsätzlich oder fahrlässig gegen die Bestimmungen der Verordnung verstoßen [2].
> 2. Bei Missachtung des Verbots der in Artikel 5 genannten KI-Praktiken werden Geldbußen von bis zu 1.500.000 EUR verhängt [4].
> 3. Bei Nichtkonformität des KI-Systems mit den in der Verordnung festgelegten Anforderungen oder Pflichten, mit Ausnahme der in Artikel 5 festgelegten, werden Geldbußen von bis zu 750.000 EUR verhängt [4].
>
> Der Kontext deckt nicht ab, ob es weitere spezifische Strafen oder Maßnahmen gibt.

Konfidenz 0,6542 (Band «mittel»), Citation-Coverage 0,6, Self-Check GEDECKT.


### `qwen3-local` — ollama_chat/qwen3:8b

**`SKOS-GBL-02`** — Wie hoch ist der Grundbedarf für einen 1-Personen-Haushalt pro Monat?

> Der Grundbedarf für einen 1-Personen-Haushalt pro Monat wird nicht explizit genannt [3]. Der Grundbedarf wird nach der Anzahl Personen in einem gemeinsam geführten Haushalt festgesetzt [3]. Für eine genaue Angabe des Betrags ist zusätzliche Information erforderlich.

Konfidenz 0,6613 (Band «mittel»), Citation-Coverage 0,6667, Self-Check GEDECKT.

**`SKOS-OOC-01`** — Wie berechnet sich die AHV-Altersrente?

> Die Berechnung der AHV-Altersrente wird nicht im Kontext-Abschnitt direkt erläutert [1][2][3][4][5].

Konfidenz 0,8424 (Band «hoch»), Citation-Coverage 1,0, Self-Check nicht gelaufen.

**`SKOS-IPV-OOC-01`** — Wie hoch ist die IPV in meinem Kanton und wie beantrage ich sie konkret?

> Die Höhe der individuellen Prämienverbilligung (IPV) ist von Kanton zu Kanton verschieden [1]. Wie konkret der Antrag auf IPV gestellt werden kann, wird im Kontext nicht abgedeckt.

Konfidenz 0,5291 (Band «mittel»), Citation-Coverage 0,5, Self-Check GEDECKT.

**`SKOS-EL-OOC-01`** — Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?

> Die Berechnung der Ergänzungsleistungen zur AHV/IV erfolgt so, dass die gekürzte Rente als Einnahme angerechnet wird, um sicherzustellen, dass keine Leistungskürzungen erfolgen und das soziale Existenzminimum im Alter gesichert ist [2]. Decken AHV- bzw. IV-Rente und der anrechenbare Vermögensverzehr aus dem Freizügigkeitsguthaben den Lebensunterhalt nicht, können Ergänzungsleistungen beantragt werden [3]. Die genaue Höhe der Ergänzungsleistungen hängt von der konkreten Situation ab und wird im Einzelfall berechnet.

Konfidenz 0,6802 (Band «mittel»), Citation-Coverage 0,6667, Self-Check GEDECKT.

**`AIA-OOC-07`** — Welche Strafen sieht das deutsche KI-Umsetzungsgesetz für Verstösse vor?

> Das deutsche KI-Umsetzungsgesetz sieht folgende Strafen für Verstöße vor:
> - Bei Verstößen gegen die einschlägigen Bestimmungen der Verordnung können Geldbußen bis zu 3 % des gesamten weltweiten Jahresumsatzes im vorangegangenen Geschäftsjahr oder 15 000 000 EUR verhängt werden, je nachdem, welcher Betrag höher ist [2].
> - Bei Missachtung des Verbots der in Artikel 5 genannten KI-Praktiken können Geldbußen von bis zu 1 500 000 EUR verhängt werden [4].
> - Bei Nichtkonformität des KI-Systems mit in der Verordnung festgelegten Anforderungen oder Pflichten, mit Ausnahme der in Artikel 5 festgelegten, können Geldbußen von bis zu 750 000 EUR verhängt werden [4].

Konfidenz 0,7292 (Band «mittel»), Citation-Coverage 0,75, Self-Check GEDECKT.

**`SAMW-OOC-03`** — Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden?

> Innerhalb von 7 Tagen [1].

Konfidenz 0,8514 (Band «hoch»), Citation-Coverage 1,0, Self-Check nicht gelaufen.

**`SAMW-OOC-06`** — Welche Detailanforderungen stellt die ICH-GCP-Leitlinie an das Monitoring klinischer Studien?

> Die ICH-GCP-Leitlinie stellt eine Reihe von Detailanforderungen an das Monitoring klinischer Studien, darunter die Normierung der Rechte und Pflichten der Prüfpersonen sowie der Sponsoren [1]. Zudem wird die Durchführung klinischer Versuche mit Arzneimitteln international einheitliche Qualitätsstandards geschaffen, um die gegenseitige Anerkennung klinischer Forschungsdaten zu erleichtern [1]. Die Leitlinie verweist auf die Helsinki-Deklaration, ist aber sehr viel detaillierter und umfassender als diese [1]. Die genaue Art der Monitoring-Anforderungen wird in den Kontext-Abschnitten nicht detailliert beschrieben.

Konfidenz 0,7113 (Band «mittel»), Citation-Coverage 0,75, Self-Check GEDECKT.


### `gemma4-local` — ollama_chat/gemma4:26b

**`SKOS-IPV-OOC-01`** — Wie hoch ist die IPV in meinem Kanton und wie beantrage ich sie konkret?

> Die Höhe der individuellen Prämienverbilligung (IPV) ist von Kanton zu Kanton verschieden [1]. Der Kontext enthält keine Informationen darüber, wie hoch die IPV in Ihrem spezifischen Kanton ist und wie man sie konkret beantragt.

Konfidenz 0,5291 (Band «mittel»), Citation-Coverage 0,5, Self-Check GEDECKT.

**`SKOS-EL-OOC-01`** — Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?

> Im Falle eines AHV-Vorbezugs wird bei der EL-Anspruchsberechnung lediglich die gekürzte Rente als Einnahme angerechnet [2]. Ergänzungsleistungen können beantragt werden, wenn die AHV- bzw. IV-Rente und der anrechenbare Vermögensverzehr aus dem Freizügigkeitsguthaben den Lebensunterhalt nicht decken [3]. Eine vollständige Berechnungsmethode für Ergänzungsleistungen wird im Kontext nicht beschrieben.

Konfidenz 0,6802 (Band «mittel»), Citation-Coverage 0,6667, Self-Check GEDECKT.

**`SAMW-OOC-03`** — Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden?

> Die Meldung von SUSAR an die Ethikkommission muss innerhalb von 7 Tagen oder innerhalb von 15 Tagen erfolgen [1]. An die lokale EK werden nur lokale Ereignisse gemeldet, während an die Leit-EK alle Ereignisse bei Studienteilnehmern in der Schweiz gemeldet werden müssen [1].

Konfidenz 0,8514 (Band «hoch»), Citation-Coverage 1,0, Self-Check nicht gelaufen.

**`SAMW-OOC-04`** — Welche Mindestversicherungssumme muss ein Sponsor für die Probandenversicherung abschliessen?

> Sponsoren sind in der Regel verpflichtet, die Haftung durch eine Versicherung oder in anderer Form sicherzustellen [2]. Eine Mindestversicherungssumme wird im Kontext nicht genannt.

Konfidenz 0,5554 (Band «mittel»), Citation-Coverage 0,5, Self-Check GEDECKT.

