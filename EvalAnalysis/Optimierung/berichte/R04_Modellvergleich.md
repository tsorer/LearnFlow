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
| `openai` | gpt-4o-mini | **90,9 %** | 22 | 2026-09-16T04-52-06Z | b7246f9 |
| `qwen3-local` | ollama_chat/qwen3:8b | **68,2 %** | 22 | 2026-09-16T05-00-52Z | b7246f9 |
| `gemma4-local` | ollama_chat/gemma4:26b | **86,4 %** | 22 | 2026-09-16T15-28-34Z | b7246f9 |
| `gpt-oss-local` | ollama_chat/gpt-oss:20b | **95,5 %** | 22 | 2026-09-16T05-19-11Z | b7246f9 |
| `ministral3-local` | ollama_chat/ministral-3:14b | **95,5 %** | 22 | 2026-09-16T13-27-52Z | b7246f9 |

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
| `SKOS-OOC-01` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-OOC-02` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-OOC-03` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-OOC-04` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-IPV-OOC-01` | Verweigerung | verweigert · Modell | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell |
| `SKOS-ALI-OOC-01` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SKOS-EL-OOC-01` | Verweigerung | verweigert · Self-Check | **ausgeliefert** ✘ | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Self-Check |
| `AIA-OOC-01` | Verweigerung | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-02` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-03` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-04` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-05` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-06` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `AIA-OOC-07` | Verweigerung | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-01` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-02` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-03` | Verweigerung | verweigert · Coverage | **ausgeliefert** ✘ | **ausgeliefert** ✘ | verweigert · Coverage | **ausgeliefert** ✘ |
| `SAMW-OOC-04` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-05` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-06` | Verweigerung | verweigert · Modell | **ausgeliefert** ✘ | verweigert · Modell | verweigert · Modell | verweigert · Modell |
| `SAMW-OOC-07` | Verweigerung | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell | verweigert · Modell |

## Woran es scheitert

Dieselben Ergebnisse, je Profil gezählt. Die Verteilung sagt mehr als die Rate: Eine
Verweigerung durch das Modell selbst ist ein anderes Verhalten als eine, die erst eine
nachgelagerte Prüfung erzwingt — im zweiten Fall hat das Modell eine Antwort
formuliert, obwohl es keine gibt.

| Profil | Verteilung |
|---|---|
| `openai` | verweigert · Modell 18, ausgeliefert 2, verweigert · Self-Check 1, verweigert · Coverage 1 |
| `qwen3-local` | verweigert · Modell 15, ausgeliefert 7 |
| `gemma4-local` | verweigert · Modell 19, ausgeliefert 3 |
| `gpt-oss-local` | verweigert · Modell 20, ausgeliefert 1, verweigert · Coverage 1 |
| `ministral3-local` | verweigert · Modell 20, verweigert · Self-Check 1, ausgeliefert 1 |

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
| `openai` | 25 | `stop` 25 | 0 | 0 | 22 s | 1,9 s | 0,7 s |
| `qwen3-local` | 23 | `stop` 23 | 0 | 0 | 112 s | 17,9 s | 3,5 s |
| `gemma4-local` | 24 | `stop` 24 | 0 | 0 | 1008 s | 129,2 s | 31,6 s |
| `gpt-oss-local` | 23 | `stop` 23 | 0 | 0 | 175 s | 18,1 s | 6,9 s |
| `ministral3-local` | 23 | `stop` 23 | 0 | 0 | 248 s | 47,0 s | 6,7 s |

Token-Verbrauch, gemessen am Anbieter. «Prompt» ist, was ans Modell geht (Anweisung,
Textabschnitte, Frage), «Completion», was es erzeugt — bei Modellen mit Denkmodus
inklusive des unsichtbaren Denkens:

| Profil | Prompt max | Prompt median | Completion max |
|---|---|---|---|
| `openai` | 2454 | 2225 | 203 |
| `qwen3-local` | 3199 | 2732 | 210 |
| `gemma4-local` | 2967 | 2330 | 2901 |
| `gpt-oss-local` | 2518 | 2289 | 222 |
| `ministral3-local` | 2927 | 2384 | 184 |

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
| `openai` | 3 von 22 | 2 | 1 | 0 |
| `qwen3-local` | 1 von 22 | 1 | 0 | 0 |
| `gemma4-local` | 2 von 22 | 2 | 0 | 0 |
| `gpt-oss-local` | 1 von 22 | 1 | 0 | 0 |
| `ministral3-local` | 1 von 22 | 0 | 1 | 0 |

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

Darunter eine **Einschätzung von Claude (KI-Assistent)**: Ist die Antwort
*inhaltlich* durch die zitierten Textabschnitte gedeckt — gedeckt, eher gedeckt, eher
ungedeckt,
ungedeckt? Das ist eine **Meinung, keine Messung**: gelesen wurden Antwort,
zitierte Abschnitte und Gold-Dataset. Fragen im Holdout (für die Schlussrunde
zurückgehalten) werden bewusst nicht beurteilt.

### `openai` — gpt-4o-mini

**`AIA-OOC-01`** — Wie berechnet sich die DSGVO-Bussgeldhöhe bei einem Datenschutzverstoss?

> Die Höhe der Geldbußen bei Datenschutzverstößen wird unter Berücksichtigung aller relevanten Umstände der jeweiligen Situation festgelegt. Dazu gehören insbesondere die Art, die Schwere und die Dauer des Verstoßes sowie dessen Folgen und die Größe des Anbieters, insbesondere wenn es sich um ein kleines oder mittleres Unternehmen (KMU) handelt [3][5].
>
> Der Europäische Datenschutzbeauftragte hat die Befugnis, Geldbußen gegen Organe, Einrichtungen und sonstige Stellen der Union zu verhängen, wobei die spezifischen Vorschriften über Geldbußen von den Mitgliedstaaten erlassen werden [5].
>
> Der Kontext deckt jedoch nicht ab, wie genau die einzelnen Faktoren in die Berechnung der Geldbußen einfließen oder welche spezifischen Beträge für bestimmte Verstöße festgelegt werden.

Konfidenz 0,5315 (Band «mittel»), Citation-Coverage 0,5, Self-Check: GEDECKT.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **ungedeckt**. Die Kriterien (Art, Schwere, Dauer, KMU-Grösse) stehen in [3][5] — aber zum AI Act, nicht zur DSGVO. Die gestellte Frage bleibt unbeantwortet, die Antwort sieht belegt aus.

**`AIA-OOC-07`** — Welche Strafen sieht das deutsche KI-Umsetzungsgesetz für Verstösse vor?

> Das deutsche KI-Umsetzungsgesetz sieht folgende Strafen für Verstöße vor:
>
> 1. Geldbußen von bis zu 3 % des gesamten weltweiten Jahresumsatzes im vorangegangenen Geschäftsjahr oder 15.000.000 EUR, je nachdem, welcher Betrag höher ist, wenn Anbieter von KI-Modellen mit allgemeinem Verwendungszweck vorsätzlich oder fahrlässig gegen die Bestimmungen der Verordnung verstoßen [2].
>
> 2. Bei Missachtung des Verbots der in Artikel 5 genannten KI-Praktiken werden Geldbußen von bis zu 1.500.000 EUR verhängt [4].
>
> 3. Bei Nichtkonformität des KI-Systems mit den in der Verordnung festgelegten Anforderungen oder Pflichten, mit Ausnahme der in Artikel 5 festgelegten, werden Geldbußen von bis zu 750.000 EUR verhängt [4].
>
> Der Kontext deckt nicht ab, ob es weitere spezifische Strafen oder Regelungen gibt.

Konfidenz 0,7292 (Band «mittel»), Citation-Coverage 0,75, Self-Check: GEDECKT.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** bewusst nicht beurteilt (Holdout-Frage).


### `qwen3-local` — ollama_chat/qwen3:8b

**`SKOS-GBL-02`** — Wie hoch ist der Grundbedarf für einen 1-Personen-Haushalt pro Monat?

> Der Grundbedarf für einen 1-Personen-Haushalt pro Monat wird nicht explizit genannt [1][2][3][4][5].

Konfidenz 0,8279 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **gedeckt**. Inhaltlich eine Verweigerung — der Betrag steht wirklich nicht im Kontext. Es fehlt nur das Format.

**`SKOS-IPV-OOC-01`** — Wie hoch ist die IPV in meinem Kanton und wie beantrage ich sie konkret?

> Die Höhe der individuellen Prämienverbilligung (IPV) ist von Kanton zu Kanton verschieden [1]. Wie die IPV konkret beantragt wird, wird nicht im Kontext erwähnt [1].

Konfidenz 0,7791 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **eher gedeckt**. «von Kanton zu Kanton verschieden» steht in [1]; der Antragsweg wird ausdrücklich als nicht abgedeckt benannt.

**`SKOS-EL-OOC-01`** — Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?

> Die Berechnung der Ergänzungsleistungen zur AHV/IV erfolgt so, dass die gekürzte Rente als Einnahme angerechnet wird, um sicherzustellen, dass keine Leistungskürzungen erfolgen und das soziale Existenzminimum im Alter gesichert ist [2]. Falls AHV- bzw. IV-Rente und der anrechenbare Vermögensverzehr aus dem Freizügigkeitsguthaben den Lebensunterhalt nicht decken, können Ergänzungsleistungen beantragt werden [3]. Der Kontext gibt keine weiteren Details zur konkreten Berechnung der Ergänzungsleistungen an.

Konfidenz 0,6802 (Band «mittel»), Citation-Coverage 0,6667, Self-Check: GEDECKT.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **eher ungedeckt**. Die zitierten Stellen betreffen den Vorbezug, nicht die Berechnung der EL; der erste Satz behauptet mehr, als [2] hergibt.

**`AIA-OOC-01`** — Wie berechnet sich die DSGVO-Bussgeldhöhe bei einem Datenschutzverstoss?

> Die DSGVO-Bussgeldhöhe bei einem Datenschutzverstoß wird im EU_AI_ACT festgelegt und beträgt bis zu 750 000 EUR [1]. Die Berechnung der Geldbuße erfolgt auf der Grundlage der Art, Schwere und Dauer des Verstoßes sowie der Größe des Anbieters [3]. Der Europäische Datenschutzbeauftragte berücksichtigt in jedem Einzelfall alle relevanten Umstände der konkreten Situation [5].

Konfidenz 0,7815 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **ungedeckt**. «wird im EU_AI_ACT festgelegt» ist eine Verwechslung, der Betrag eine AI-Act-Zahl. Coverage 1,0 — die Antwort sieht vollständig belegt aus.

**`AIA-OOC-07`** — Welche Strafen sieht das deutsche KI-Umsetzungsgesetz für Verstösse vor?

> Das deutsche KI-Umsetzungsgesetz sieht folgende Strafen für Verstöße vor:
> - Bei Verstößen gegen die einschlägigen Bestimmungen der Verordnung können Geldbußen von bis zu 3 % des gesamten weltweiten Jahresumsatzes im vorangegangenen Geschäftsjahr oder 15 000 000 EUR verhängt werden [2].
> - Bei Missachtung des Verbots der in Artikel 5 genannten KI-Praktiken werden Geldbußen von bis zu 1 500 000 EUR verhängt [4].
> - Bei Nichtkonformität des KI-Systems mit in der Verordnung festgelegten Anforderungen oder Pflichten, mit Ausnahme der in Artikel 5 festgelegten, werden Geldbußen von bis zu 750 000 EUR verhängt [4].

Konfidenz 0,8542 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** bewusst nicht beurteilt (Holdout-Frage).

**`SAMW-OOC-03`** — Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden?

> Innert 7 Tagen [1].

Konfidenz 0,8514 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **gedeckt**. Die 7 Tage stehen in [1]; die zweite Frist (15 Tage) fehlt, erfunden ist nichts.

**`SAMW-OOC-06`** — Welche Detailanforderungen stellt die ICH-GCP-Leitlinie an das Monitoring klinischer Studien?

> Die ICH-GCP-Leitlinie legt keine spezifischen Detailanforderungen an das Monitoring klinischer Studien fest, da sie sich primär auf die Durchführung klinischer Versuche mit Arzneimitteln konzentriert und nicht explizit auf Monitoring-Verfahren eingehen [1].

Konfidenz 0,8363 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** bewusst nicht beurteilt (Holdout-Frage).


### `gemma4-local` — ollama_chat/gemma4:26b

**`SKOS-IPV-OOC-01`** — Wie hoch ist die IPV in meinem Kanton und wie beantrage ich sie konkret?

> Die Höhe und die Art der individuellen Prämienverbilligung (IPV) sowie die konkreten Anspruchsvoraussetzungen sind von Kanton zu Kanton verschieden [1]. Der Kontext deckt die Höhe der IPV in Ihrem Kanton sowie den konkreten Antragsprozess nicht ab.

Konfidenz 0,5291 (Band «mittel»), Citation-Coverage 0,5, Self-Check: GEDECKT.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **gedeckt**. «von Kanton zu Kanton verschieden» steht in [1], die Lücke wird benannt — inhaltlich nahe an einer Verweigerung.

**`SKOS-EL-OOC-01`** — Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?

> Der Kontext gibt nur teilweise Auskunft über die Berechnung der Ergänzungsleistungen (EL). Im Falle eines AHV-Vorbezugs wird bei der EL-Anspruchsberechnung lediglich die gekürzte Rente als Einnahme angerechnet [2]. Ergänzungsleistungen können beantragt werden, wenn die AHV- bzw. IV-Rente und der anrechenbare Vermögensverzehr aus dem Freizügigkeitsguthaben den Lebensunterhalt nicht decken [3]. Der Kontext erläutert nicht die vollständige Berechnungsmethode oder die genauen Parameter zur Ermittlung der EL-Höhe.

Konfidenz 0,5968 (Band «mittel»), Citation-Coverage 0,5, Self-Check: GEDECKT.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **eher gedeckt**. Der Vorbezugs-Sonderfall steht in [2], der Antragsgrund in [3]; die fehlende Berechnungsmethode wird ausdrücklich benannt.

**`SAMW-OOC-03`** — Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden?

> Die Meldung von SUSAR (Suspected Unexpected Serious Adverse Reaction) an die Ethikkommission erfolgt an die lokale EK nur bei lokalen Ereignissen, während alle Ereignisse bei Studienteilnehmern in der Schweiz an die Leit-EK gemeldet werden müssen [1]. Die genannten Fristen sind innerhalb von 7 Tagen [1] sowie innerhalb von 15 Tagen [1]. Der Kontext gibt nicht an, welche Kriterien für die Unterscheidung zwischen diesen beiden Fristen bei SUSAR gelten [1].

Konfidenz 0,8514 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **gedeckt**. Fristen und Zuständigkeiten stehen in [1]. Von allen fünf Profilen die genaueste Lesart: nennt beide Fristen und sagt ausdrücklich, dass der Kontext das Unterscheidungskriterium nicht hergibt — was stimmt, weil die Spaltensemantik der Tabelle im Textlayer verloren geht.


### `gpt-oss-local` — ollama_chat/gpt-oss:20b

**`SKOS-EL-OOC-01`** — Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?

> Ergänzungsleistungen (EL) werden so berechnet, dass bei einem AHV‑Vorzug lediglich die gekürzte AHV‑Rente als Einnahme angerechnet wird. Damit soll sichergestellt werden, dass keine Leistungskürzungen erfolgen und das soziale Existenzminimum im Alter gesichert bleibt. [2]

Konfidenz 0,5968 (Band «mittel»), Citation-Coverage 0,5, Self-Check: GEDECKT.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **ungedeckt**. [2] beschreibt den Vorbezug, nicht die Berechnung der EL; die Antwort liest sich als vollständige Auskunft.


### `ministral3-local` — ollama_chat/ministral-3:14b

**`SAMW-OOC-03`** — Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden?

> Innerhalb von **7 Tagen** müssen schwerwiegende unerwünschte Ereignisse (SUSAR) der Ethikkommission gemeldet werden, wenn sie mit Todesfolge verbunden sind oder ein Verdacht auf eine unerwartete Arzneimittelwirkung besteht [1].
>
> Für **übrige SUSAR** (ohne Todesfolge) gilt eine Frist von **15 Tagen** [1].
>
> Der Kontext deckt nicht ab:
> - Meldefristen für SUSAR in anderen Kontexten als klinischen Versuchen mit Arzneimitteln oder Medizinprodukten [1].
> - Meldepflichten außerhalb der Schweiz oder für andere Arten von KI-Systemen [2][3].

Konfidenz 0,8514 (Band «hoch»), Citation-Coverage 1,0, Self-Check: nicht gelaufen.

**Einschätzung Claude (KI-Assistent) — Meinung, keine Messung:** inhaltlich **eher gedeckt**. Beide Fristen (7 und 15 Tage) stehen in der Meldefristen-Tabelle von [1]. Die Zuordnung «Todesfolge → 7 Tage» steht dort aber nur in der SAE-Zeile darüber; die SUSAR-Zeile nennt bloss zwei gleich beschriftete Spalten. Ministral schliesst das aus der Nachbarzeile — inhaltlich vermutlich richtig, aus dem flachgezogenen Tabellentext nicht belegbar.

