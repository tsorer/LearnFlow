# Eval-Messreihe — Modellvergleich

Erzeugt mit `python -m eval.compare` aus den Läufen unten — nicht von Hand ändern,
Einordnungen gehören in ein eigenes Dokument.

## Worum es geht

LearnFlow beantwortet Fragen ausschliesslich aus hochgeladenen Dokumenten. Steht die
Antwort nicht darin, soll das System **verweigern** («Weiss ich nicht»), statt etwas zu
erfinden. Dieser Bericht prüft genau das: Jede der Fragen unten ist so gewählt, dass
die Antwort **nicht** in den Dokumenten steht (Out-of-Corpus-Fragen aus dem
Gold-Dataset, einer fachlich abgenommenen Fragensammlung). Richtig ist laut
Gold-Dataset also immer die Verweigerung.

Eine Antwort durchläuft mehrere Stufen. Jede kann verweigern:

| Stufe | prüft | verweigert, wenn … |
|---|---|---|
| Retrieval | Suche nach passenden Textabschnitten | nichts ausreichend Ähnliches gefunden wird |
| Modell | Das Sprachmodell formuliert die Antwort aus den Abschnitten | das Modell selbst mit `WEISS_NICHT` antwortet |
| Coverage | Trägt jede Aussage einen Beleg `[n]` auf einen Abschnitt? | zu wenige Aussagen belegt sind |
| Self-Check | Dasselbe Modell prüft in einem zweiten Aufruf seine eigene Antwort | es nicht mit `GEDECKT` urteilt |

Wird an keiner Stufe verweigert, wird die Antwort **ausgeliefert**.

## Läufe

Je Profil (Modell mit seinen Einstellungen) der neueste Lauf. **Korrekt verweigert** ist
der Anteil der Fragen, bei denen das System wie erwartet verweigert hat — höher ist
besser. **Lauf** ist der Zeitstempel (UTC) des Ergebnisordners, **Git-SHA** der
Code-Stand der Messung.

| Profil | Modell | korrekt verweigert | Fragen | Lauf | Git-SHA |
|---|---|---|---|---|---|
| `openai` | gpt-4o-mini | **95,5 %** | 22 | 2026-09-15T19-21-03Z | 02eefb7 |
| `qwen3-local` | ollama_chat/qwen3:8b | **59,1 %** | 22 | 2026-09-15T19-29-42Z | 02eefb7 |
| `gemma4-local` | ollama_chat/gemma4:26b | **81,8 %** | 22 | 2026-09-15T16-24-27Z | 0dedbaa |
| `gpt-oss-local` | ollama_chat/gpt-oss:20b | **90,9 %** | 22 | 2026-09-15T19-44-48Z | 02eefb7 |
| `ministral3-local` | ollama_chat/ministral-3:14b | **100,0 %** | 22 | 2026-09-15T20-19-20Z | 02eefb7 |

## Wirksame Schwellen

Die Grenzwerte, gegen die jede Stufe entschieden hat. Nur wenn sie in allen Läufen
gleich sind, unterscheiden sich die Profile allein durch das Modell.

Über alle Läufe identisch (Seed-Defaults), die Raten sind vergleichbar:

| Parameter | Wert | Bedeutung |
|---|---|---|
| `confidence_threshold_high` | 0.75 | Konfidenz ab hier Band «hoch» |
| `confidence_threshold_medium` | 0.45 | Konfidenz ab hier Band «mittel», darunter «niedrig» |
| `context_top_n` | 5 | Anzahl Textabschnitte, die das Modell als Kontext bekommt |
| `min_citation_coverage` | 0.5 | Mindestanteil der Aussagen einer Antwort, die einen Beleg [n] tragen |
| `min_retrieval_confidence` | 0.4 | Mindestqualität der Treffer, sonst Verweigerung vor dem Modell |
| `retrieval_top_k` | 20 | Anzahl Textabschnitte, die die Suche holt |
| `rrf_k` | 60 | Glättung beim Zusammenführen von Vektor- und Volltextsuche |
| `self_check_band_high` | 0.75 | Obergrenze des Bereichs, in dem der Self-Check läuft |
| `self_check_band_low` | 0.45 | Untergrenze des Bereichs, in dem der Self-Check läuft |
| `similarity_threshold` | 0.35 | Mindestähnlichkeit, ab der ein Textabschnitt als Treffer zählt |

## Pro Frage

Was mit jeder Frage passiert ist. Eine Zelle nennt entweder die Stufe, die verweigert
hat, oder «ausgeliefert». **✘ markiert einen Fehler**: das Ergebnis
weicht von der Erwartung ab. Alles ohne Markierung ist richtig.

| Eintrag | Bedeutung | richtig, wenn Verweigerung erwartet? |
|---|---|---|
| verweigert · Modell | Das Modell hat selbst `WEISS_NICHT` geantwortet | ja |
| verweigert · Coverage | Antwort erzeugt, aber zu wenig belegt | ja |
| verweigert · Self-Check | Antwort erzeugt, bei der Selbstprüfung verworfen | ja |
| verweigert · Retrieval | Keine passenden Textabschnitte, Modell nie gefragt | ja |
| ausgeliefert ✘ | Antwort ging an den Nutzer | **nein** |

| Frage | erwartet | `openai` | `qwen3-local` | `gemma4-local` | `gpt-oss-local` | `ministral3-local` |
|---|---|---|---|---|---|---|
| `SKOS-GBL-02` | Verweigerung | verweigert · Modell | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-OOC-01` | Verweigerung | verweigert · Modell | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-OOC-02` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-OOC-03` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-OOC-04` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-IPV-OOC-01` | Verweigerung | verweigert · Modell | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell |
| `SKOS-ALI-OOC-01` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-EL-OOC-01` | Verweigerung | verweigert · Coverage | **ausgeliefert** ✘ | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Self-Check |
| `AIA-OOC-01` | Verweigerung | verweigert · Modell | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-02` | Verweigerung | verweigert · Modell | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-03` | Verweigerung | verweigert · Modell | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-04` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-05` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-06` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-07` | Verweigerung | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-01` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-02` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-03` | Verweigerung | verweigert · Coverage | **ausgeliefert** ✘ | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Self-Check |
| `SAMW-OOC-04` | Verweigerung | verweigert · Modell | verweigert · Modell | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-05` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-06` | Verweigerung | verweigert · Modell | verweigert · Self-Check | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-07` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |

## Woran es scheitert

Dieselben Ergebnisse, je Profil gezählt. Die Verteilung sagt mehr als die Rate: Eine
Verweigerung durch das Modell selbst ist ein anderes Verhalten als eine, die erst eine
nachgelagerte Prüfung erzwingt — im zweiten Fall hat das Modell eine Antwort
formuliert, obwohl es keine gibt.

| Profil | Verteilung |
|---|---|
| `openai` | verweigert · Modell 19, verweigert · Coverage 2, ausgeliefert 1 |
| `qwen3-local` | verweigert · Modell 12, ausgeliefert 9, verweigert · Self-Check 1 |
| `gemma4-local` | verweigert · Modell 18, ausgeliefert 4 |
| `gpt-oss-local` | verweigert · Modell 20, ausgeliefert 2 |
| `ministral3-local` | verweigert · Modell 20, verweigert · Self-Check 2 |

## LLM-Aufrufe

Kontrolle, ob die Messung überhaupt gültig ist. Gezählt werden alle Aufrufe an das
Modell — die Antwort und, wo er lief, der Self-Check. `finish_reason` meldet, warum
das Modell aufgehört hat: `stop` heisst fertig, `length` heisst am Token-Limit
abgeschnitten. Ein abgeschnittener oder leerer Aufruf misst das Limit, nicht das
Modell. **`length` darf in der Spalte finish_reason nicht vorkommen und «leer» muss 0
sein**, sonst sind die Raten oben nicht aussagekräftig. Die Dauer hängt von der
Hardware ab und ist nur zwischen Läufen auf demselben Rechner vergleichbar.

| Profil | Aufrufe | finish_reason | leer | Fehler | Σ Dauer | max | median |
|---|---|---|---|---|---|---|---|
| `openai` | 23 | `stop` 23 | 0 | 0 | 17 s | 2,0 s | 0,7 s |
| `qwen3-local` | 26 | `stop` 26 | 0 | 0 | 148 s | 15,8 s | 4,5 s |
| `gemma4-local` | 25 | `stop` 25 | 0 | 0 | 1036 s | 93,3 s | 37,3 s |
| `gpt-oss-local` | 23 | `stop` 23 | 0 | 0 | 163 s | 15,1 s | 6,6 s |
| `ministral3-local` | 24 | `stop` 24 | 0 | 0 | 256 s | 44,4 s | 5,6 s |

Token-Verbrauch, gemessen am Anbieter. «Prompt» ist, was ans Modell geht (Anweisung,
Textabschnitte, Frage), «Completion», was es erzeugt — bei Modellen mit Denkmodus
inklusive des unsichtbaren Denkens:

| Profil | Prompt max | Prompt median | Completion max |
|---|---|---|---|
| `openai` | 2370 | 2161 | 198 |
| `qwen3-local` | 3102 | 2690 | 222 |
| `gemma4-local` | 2835 | 2267 | 1964 |
| `gpt-oss-local` | 2434 | 2205 | 186 |
| `ministral3-local` | 2841 | 2338 | 187 |

## Self-Check

Nach der Antwort fragt die Pipeline **dasselbe Modell ein zweites Mal**: Ist jede
Aussage der Antwort durch die Textabschnitte gedeckt? Verlangt ist exakt
`GEDECKT` oder `NICHT_GEDECKT:` mit den nicht gedeckten Aussagen. Die
Spalten zeigen, was das Modell geantwortet hat, so wie die Pipeline es automatisch
gelesen hat:

- **GEDECKT** — Antwort wird ausgeliefert.
- **NICHT_GEDECKT** — Antwort wird verweigert.
- **andere Antwort** — weder das eine noch das andere (leer, Prosa, `GEDECKT` mit Zusatz). Die Pipeline kann das Urteil **nicht automatisch
  auswerten** und verweigert vorsichtshalber.

Der Self-Check läuft nur, wenn die Konfidenz der Antwort im mittleren Bereich liegt;
sehr sichere und sehr unsichere Antworten werden nicht geprüft. Wie oft er läuft, ist
deshalb selbst ein Befund.

| Profil | gelaufen | GEDECKT | NICHT_GEDECKT | andere Antwort |
|---|---|---|---|---|
| `openai` | 1 von 22 | 1 | 0 | 0 |
| `qwen3-local` | 4 von 22 | 3 | 1 | 0 |
| `gemma4-local` | 3 von 22 | 3 | 0 | 0 |
| `gpt-oss-local` | 1 von 22 | 1 | 0 | 0 |
| `ministral3-local` | 2 von 22 | 0 | 2 | 0 |

## Abweichungen im Wortlaut

**Vollständig, keine Auswahl:** jede Antwort, die ausgeliefert wurde, obwohl eine
Verweigerung erwartet war — also jede Zelle mit ✘ oben —, im Originaltext, den der
Nutzer gesehen hätte. Korrekt verweigerte Fragen erscheinen hier nicht; sie haben
keinen ausgelieferten Text.

Die Kennzahlen unterscheiden nicht zwischen einer erfundenen Aussage und einer
inhaltlich richtigen Verweigerung, die nur nicht im geforderten Format
(`WEISS_NICHT`) kam. Das lässt sich nur am Text erkennen — die Einordnung macht ein
Mensch, in einem eigenen Dokument.

Unter jeder Antwort: **Konfidenz** (0–1, aus Suchqualität und Belegdichte) mit ihrem
**Band**, **Citation-Coverage** (Anteil belegter Aussagen, 0–1) und das Ergebnis des
**Self-Checks**.

### `openai` — gpt-4o-mini

**`AIA-OOC-07`** — Welche Strafen sieht das deutsche KI-Umsetzungsgesetz für Verstösse vor?

> Das deutsche KI-Umsetzungsgesetz sieht folgende Strafen für Verstöße vor:
>
> 1. Geldbußen von bis zu 3 % des gesamten weltweiten Jahresumsatzes im vorangegangenen Geschäftsjahr oder 15 000 000 EUR, je nachdem, welcher Betrag höher ist, wenn Anbieter von KI-Modellen mit allgemeinem Verwendungszweck vorsätzlich oder fahrlässig gegen die Bestimmungen verstoßen [2].
> 2. Bei Missachtung des Verbots der in Artikel 5 genannten KI-Praktiken werden Geldbußen von bis zu 1 500 000 EUR verhängt [4].
> 3. Bei Nichtkonformität des KI-Systems mit den in dieser Verordnung festgelegten Anforderungen oder Pflichten, mit Ausnahme der in Artikel 5 festgelegten, werden Geldbußen von bis zu 750 000 EUR verhängt [4].
>
> Der Kontext deckt nicht ab, ob es weitere spezifische Strafen oder Maßnahmen gibt.

Konfidenz 0,7292 (Band «mittel»), Citation-Coverage 0,75, Self-Check: GEDECKT.


### `qwen3-local` — ollama_chat/qwen3:8b

**`SKOS-GBL-02`** — Wie hoch ist der Grundbedarf für einen 1-Personen-Haushalt pro Monat?

> Der Grundbedarf für einen 1-Personen-Haushalt pro Monat wird nicht explizit genannt [3]. Der Grundbedarf wird nach der Anzahl Personen in einem gemeinsam geführten Haushalt festgesetzt [3].

Konfidenz 0,8279 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**`SKOS-OOC-01`** — Wie berechnet sich die AHV-Altersrente?

> Die Berechnung der AHV-Altersrente wird in den Kontext-Abschnitten nicht detailliert beschrieben [1][2][3][4][5].

Konfidenz 0,8424 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**`SKOS-IPV-OOC-01`** — Wie hoch ist die IPV in meinem Kanton und wie beantrage ich sie konkret?

> Die Höhe der individuellen Prämienverbilligung (IPV) ist von Kanton zu Kanton verschieden [1]. Wie die IPV konkret beantragt wird, wird nicht im Kontext abgedeckt.

Konfidenz 0,5291 (Band «mittel»), Citation-Coverage 0,5, Self-Check: GEDECKT.

**`SKOS-EL-OOC-01`** — Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?

> Die Berechnung der Ergänzungsleistungen zur AHV/IV erfolgt so, dass die gekürzte Rente als Einnahme angerechnet wird, um sicherzustellen, dass keine Leistungskürzungen erfolgen und das soziale Existenzminimum im Alter gesichert ist [2]. Decken AHV- bzw. IV-Rente und der anrechenbare Vermögensverzehr aus dem Freizügigkeitsguthaben den Lebensunterhalt nicht, können Ergänzungsleistungen beantragt werden [3]. Die genaue Höhe der Ergänzungsleistungen hängt von der konkreten Situation ab und wird im Einzelfall berechnet.

Konfidenz 0,6802 (Band «mittel»), Citation-Coverage 0,6667, Self-Check: GEDECKT.

**`AIA-OOC-01`** — Wie berechnet sich die DSGVO-Bussgeldhöhe bei einem Datenschutzverstoss?

> Die DSGVO-Bussgeldhöhe bei einem Datenschutzverstoß wird auf der Grundlage der Art, der Schwere und der Dauer des Verstoßes sowie seiner Folgen berechnet [3]. Die Höhe der Geldbuße wird zudem an die Größe des Anbieters angepasst, insbesondere wenn es sich um ein KMU handelt [3]. Die Mitgliedstaaten können zusätzliche Vorschriften zur Festsetzung der Geldbußen erlassen [5].

Konfidenz 0,7815 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**`AIA-OOC-02`** — Ist ChatGPT von OpenAI gemäss EU AI Act als hochriskantes KI-System klassifiziert?

> Die Klassifizierung von ChatGPT als hochriskantes KI-System gemäß EU AI Act wird nicht direkt im Kontext erwähnt [1][2][3][4][5]. Es wird jedoch beschrieben, unter welchen Bedingungen KI-Systeme als hochriskant eingestuft werden können, beispielsweise wenn sie das Ergebnis der Entscheidungsfindung wesentlich beeinflussen [3]. Da keine spezifische Information über ChatGPT vorliegt, kann keine eindeutige Klassifizierung erfolgen.

Konfidenz 0,6734 (Band «mittel»), Citation-Coverage 0,6667, Self-Check: GEDECKT.

**`AIA-OOC-03`** — Welche nationalen Behörden in der Schweiz sind für die Umsetzung des EU AI Act zuständig?

> Die Frage kann nicht vollständig beantwortet werden, da der Kontext keine spezifischen Informationen über die Schweiz enthält [1][2][3][4][5].

Konfidenz 0,8136 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**`AIA-OOC-07`** — Welche Strafen sieht das deutsche KI-Umsetzungsgesetz für Verstösse vor?

> Das deutsche KI-Umsetzungsgesetz sieht folgende Strafen für Verstöße vor:
> - Bei Verstößen gegen die einschlägigen Bestimmungen der Verordnung können Geldbußen bis zu 3 % des gesamten weltweiten Jahresumsatzes im vorangegangenen Geschäftsjahr oder 15 000 000 EUR verhängt werden, je nachdem, welcher Betrag höher ist [2].
> - Bei Missachtung des Verbots der in Artikel 5 genannten KI-Praktiken können Geldbußen von bis zu 1 500 000 EUR verhängt werden [4].
> - Bei Nichtkonformität des KI-Systems mit in der Verordnung festgelegten Anforderungen oder Pflichten, mit Ausnahme der in Artikel 5 festgelegten, können Geldbußen von bis zu 750 000 EUR verhängt werden [4].

Konfidenz 0,8542 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**`SAMW-OOC-03`** — Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden?

> Innerhalb von 7 Tagen [1].

Konfidenz 0,8514 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.


### `gemma4-local` — ollama_chat/gemma4:26b

**`SKOS-IPV-OOC-01`** — Wie hoch ist die IPV in meinem Kanton und wie beantrage ich sie konkret?

> Die Höhe der individuellen Prämienverbilligung (IPV) ist von Kanton zu Kanton verschieden [1]. Der Kontext enthält keine Informationen darüber, wie hoch die IPV in Ihrem spezifischen Kanton ist und wie man sie konkret beantragt.

Konfidenz 0,5291 (Band «mittel»), Citation-Coverage 0,5, Self-Check: GEDECKT.

**`SKOS-EL-OOC-01`** — Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?

> Im Falle eines AHV-Vorbezugs wird bei der EL-Anspruchsberechnung lediglich die gekürzte Rente als Einnahme angerechnet [2]. Ergänzungsleistungen können beantragt werden, wenn die AHV- bzw. IV-Rente und der anrechenbare Vermögensverzehr aus dem Freizügigkeitsguthaben den Lebensunterhalt nicht decken [3]. Eine vollständige Berechnungsmethode für Ergänzungsleistungen wird im Kontext nicht beschrieben.

Konfidenz 0,6802 (Band «mittel»), Citation-Coverage 0,6667, Self-Check: GEDECKT.

**`SAMW-OOC-03`** — Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden?

> Die Meldung von SUSAR an die Ethikkommission muss innerhalb von 7 Tagen oder innerhalb von 15 Tagen erfolgen [1]. An die lokale EK werden nur lokale Ereignisse gemeldet, während an die Leit-EK alle Ereignisse bei Studienteilnehmern in der Schweiz gemeldet werden müssen [1].

Konfidenz 0,8514 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**`SAMW-OOC-04`** — Welche Mindestversicherungssumme muss ein Sponsor für die Probandenversicherung abschliessen?

> Sponsoren sind in der Regel verpflichtet, die Haftung durch eine Versicherung oder in anderer Form sicherzustellen [2]. Eine Mindestversicherungssumme wird im Kontext nicht genannt.

Konfidenz 0,5554 (Band «mittel»), Citation-Coverage 0,5, Self-Check: GEDECKT.


### `gpt-oss-local` — ollama_chat/gpt-oss:20b

**`SKOS-EL-OOC-01`** — Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?

> Ergänzungsleistungen (EL) werden berechnet, indem bei der Anspruchsberechnung ausschließlich die gekürzte AHV‑Rente als Einnahme angerechnet wird. Alle anderen Einkünfte, die aus der AHV/IV stammen, werden nicht berücksichtigt, sodass keine Leistungskürzungen erfolgen und das soziale Existenzminimum im Alter gesichert bleibt. [2]

Konfidenz 0,5968 (Band «mittel»), Citation-Coverage 0,5, Self-Check: GEDECKT.

**`SAMW-OOC-03`** — Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden?

> Innerhalb von 7 Tagen. [1]

Konfidenz 0,8514 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.


### `ministral3-local` — ollama_chat/ministral-3:14b

Keine Abweichung.
