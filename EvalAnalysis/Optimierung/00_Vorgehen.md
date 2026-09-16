# RAG-Pipeline-Optimierung — Vorgehen

Rahmen für eine schrittweise, nachvollziehbare Optimierung der LearnFlow-RAG-Pipeline
über mehrere Sprachmodelle hinweg. Teil der CAS-Abschlussarbeit.

Dieses Dokument legt fest, **wie** optimiert wird — bevor die erste Änderung gemacht ist.
Die Runden-Dokumente (`R00_…`, `R01_…`) halten fest, **was** gemessen, gefolgert und
entschieden wurde. Entscheide, die das ausgelieferte System verändern (Prompt, Modell,
Budgets), gehören zusätzlich als Nachtrag in das zuständige ADR (`Docs/`).

## 1. Ziele

1. **Produktivmodell finden**, das mindestens so gut ist wie die Referenz
   `gpt-4o-mini` (Profil `openai`) — gemessen an den Kriterien in Abschnitt 5.
2. **Pipeline verbessern**, vor allem dort, wo Modelle inhaltlich richtig entscheiden,
   aber nicht im geforderten Format antworten.
3. **Know-how aufbauen**: welche Stellschraube wirkt wie, bei welchem Modell, und warum.
   Das Lernen ist gleichrangig mit dem Ergebnis — eine Runde, deren Hypothese sich nicht
   bestätigt, ist ein gültiges Resultat, solange sie begründet und dokumentiert ist.

## 2. Leitthese

> **Sprachmodelle sind in einer fail-closed RAG-Pipeline nicht austauschbar.**
> Ein Modellwechsel verändert nicht nur die Antwortqualität, sondern vor allem, ob das
> Modell das Ausgabeprotokoll der Pipeline bedient (`WEISS_NICHT`, Fussnoten `[n]`,
> `GEDECKT`/`NICHT_GEDECKT`). Ein Modell kann richtig urteilen und trotzdem als Fehler
> zählen — oder umgekehrt.

Die Messreihe vom 2026-09-10 hat das erstmals gezeigt: sechs von zwölf «Fehlern» waren
inhaltlich korrekte Verweigerungen in Prosa (`2026-09-10_Befunde.md`, Punkt 2). Die
Optimierung soll diese These prüfen und quantifizieren.

## 3. Scope

| Im Fokus | Bewusst fix gehalten |
|---|---|
| Generierungs-Prompt (`app/services/generation.py`) | Schwellen (`similarity_threshold`, `min_citation_coverage`, Bänder) — Seed-Defaults, Parametrisierung ist T-57 |
| Self-Check-Prompt und -Parser (`app/services/self_check.py`) | Retrieval (Chunking, `retrieval_top_k`, `context_top_n`, RRF) — bei allen Modellen identisch |
| Modellwahl und modellspezifische Einstellungen (Profil: `think`, `num_ctx`, Budgets) | `TEMPERATURE = 0.0` |
| Protokoll-Erkennung (`_is_refusal`, Satz-/Fussnotenerkennung in `confidence.py`) | Korpus und Gold-Dataset (ausser in der Holdout-Aufteilung, Abschnitt 7) |

Schwellen bleiben fix, damit jede Veränderung einer Kennzahl einer Prompt- oder
Modelländerung zugeordnet werden kann. Eine Fail-closed-Schwelle wird in dieser Arbeit
nicht gelockert (ADR-008).

## 4. Stellschrauben-Landkarte

Wo eine Antwort auf dem Weg durch die Pipeline hängen bleiben kann — und welcher Hebel dort
ansetzt. Grundlage für die Hypothesen jeder Runde.

| Stufe | Unterdrückungsgrund | Was das Modell dafür tun muss | Hebel |
|---|---|---|---|
| 0/1 Retrieval | `retrieval_gate`, `retrieval_confidence` | — (modellunabhängig) | fix |
| 2a Generierung | `generation_refused` | genau `WEISS_NICHT`, wenn nicht gedeckt — und *nur* dann | Prompt Regel 3/4, Beispiele, Modell |
| 2a Generierung | `generation_truncated` | innerhalb `max_tokens` fertig werden | Budget, `think` |
| 2b Citation-Coverage | `citation_coverage` | jede Aussage mit `[n]` direkt hinter dem Satz belegen | Prompt Regel 2, Zitierbeispiel, Satzsplitter |
| 3 Self-Check | `self_check` | Urteil exakt als `GEDECKT` bzw. `NICHT_GEDECKT: …` | Self-Check-Prompt, Parser, Budget |

**Token- und Zeitbudgets:** In der Eval überschreiben die lokalen Profile Budgets und
Timeouts (z. B. `max_verdict_tokens` 4000 statt 300, Timeout 1800 s statt 30 s). Das ist
gewollt und wird in dieser Optimierung **nicht als Eignungskriterium** gewertet: Die
Budgets sind so grosszügig, dass kein Abbruch die Messung verfälscht (Abschnitt 5, Stufe 1).
Das Performance-NFA der Produktion (p95 ≤ 10 s, T-22) gilt für die Zielhardware, nicht für
die Testhardware (Abschnitt 5a).

## 5. Kriterien — festgelegt vor Runde 1

Die Prüfung erfolgt in dieser Reihenfolge. Ein Lauf, der an Stufe 1 scheitert, wird nicht
bewertet.

| Stufe | Kriterium | Wert | Quelle |
|---|---|---|---|
| 1. Gültigkeit | `finish_reason = length` | 0 | `details.json` / `compare.py` |
| | leere Antworten, Aufruffehler | 0 | ebd. |
| 2. Harte Grenzen | Halluzinationsrate (H1/H2) | 0 % | ADR-009 |
| | Out-of-Corpus-Refusal | ≥ 90 % | ADR-009 |
| 3. Vergleich zur Referenz | Out-of-Corpus-Refusal | ≥ Referenz (Unsicherheit siehe unten) | |
| | False-Suppression | ≤ Referenz | |
| | Fehlklassen F1/F2 (Abschnitt 6) | ≤ Referenz | manuelle Einordnung |
| 4. Betrieb | im Zielbetrieb verfügbar | Azure OpenAI EU oder on-prem | ADR-004 |
| | lauffähig auf der Testhardware | ja (Abschnitt 5a) | |

**Rauschen und Auflösung.** Eine Frage entspricht 4,5 Prozentpunkten (Out-of-Corpus, n=22)
bzw. 2,2 Prozentpunkten (In-Corpus, n=45). Die Referenz ist trotz Temperatur 0 nicht
deterministisch (Refusal 91–95,5 %, False-Suppression 31–38 % über mehrere Läufe); die
lokalen Modelle waren am 2026-09-14 über zwei Läufe am selben Abend Frage für Frage identisch,
einen Tag später bei gleicher Eingabe aber nicht mehr (gpt-oss 48 von 80 wortgleich, R01).
Auch lokal ist ein Einzellauf also nur innerhalb einer Sitzung reproduzierbar.
Deshalb:

- Jedes Profil wird pro Runde **einmal** gemessen, auch die Referenz. Das genügt für grobe
  Aussagen und hält die Rundendauer tragbar.
- Das bekannte Streuband der Referenz (oben) gilt als Unsicherheit ihres Einzelwerts.
- Ein Unterschied von **einer Frage** gilt nicht als Effekt; Aussagen stützen sich auf
  Unterschiede von mehreren Fragen oder auf ein wiederkehrendes Muster über Runden.

## 5a. Testhardware und Laufzeiten

Die lokalen Modelle laufen bewusst auf **minimaler Testhardware**:

| Komponente | Testhardware |
|---|---|
| GPU | NVIDIA GeForce RTX 3070 Laptop, 8 GB VRAM |
| RAM | 32 GB |
| CPU | Intel Core i7-11800H |
| Laufzeit | Ollama (lokal), Eval im `api`-Container |

Die Testhardware spiegelt **nicht** die Zielhardware. Sie hat zwei Aufgaben:

1. **Filter gegen teure Modelle.** Was hier nicht lauffähig ist, wird nicht evaluiert. Damit
   landet kein Modell in der Auswahl, das sich nur mit sehr teurer Hardware betreiben liesse.
2. **Datenbasis für die Dimensionierung.** Laufzeiten sind hier kein Ausschlusskriterium,
   werden aber je Modell und Runde festgehalten — als Grundlage, um abzuschätzen, welche
   Zielhardware die Produktionsvorgaben (p95 ≤ 10 s, T-22) einhalten würde und was der
   Betrieb kostet.

Je Modell erfasst (aus `details.json`, `llm_trace`):

- Dauer je Aufruf: Median, p95, Maximum — getrennt nach Generierung und Self-Check;
- Prompt- und Completion-Tokens (Median, Maximum) und daraus Tokens pro Sekunde;
- Aufteilung CPU/GPU laut `ollama ps` (wie viel des Modells passt in den VRAM);
- Gesamtdauer der Runde.

Vergleiche zwischen Modellen sind nur auf derselben Hardware und bei sonst ungenutztem
Rechner aussagekräftig: Am 2026-09-14 verlängerte knapper Arbeitsspeicher dieselbe Messung
um 11–17 %, ohne ein einziges Ergebnis zu verändern.

## 6. Einordnung der Abweichungen — die zentrale Messgrösse

Die Kennzahlen zählen nur, *ob* die Pipeline unterdrückt hat. Für die Leitthese braucht es
zusätzlich, *warum* — und ob das Modell inhaltlich richtig lag. Jede Abweichung von der
Erwartung des Gold-Datasets wird von Hand einer Klasse zugeordnet und kurz begründet.

**Out-of-Corpus, ausgeliefert statt verweigert**

| Klasse | Bedeutung | Urteil | Protokoll | Typischer Hebel |
|---|---|---|---|---|
| **P1** Prosa-Verweigerung | «steht nicht im Kontext», ohne `WEISS_NICHT` | richtig | verletzt | Prompt Regel 3, Beispiel |
| **P2** Teilantwort mit benannter Lücke | Regel 4 korrekt befolgt, Gold erwartet Verweigerung | vertretbar | eingehalten | Prompt Regel 3 vs. 4 schärfen — oder Gold-Frage prüfen |
| **F1** Verwechslung | belegte Aussage zu einem anderen Gegenstand (z. B. `AIA-OOC-07`) | falsch | eingehalten | Prompt, Self-Check |
| **F2** Erfindung | nicht belegte Aussage | falsch | — | Self-Check, Modell |

**In-Corpus, unterdrückt statt ausgeliefert**

| Klasse | Bedeutung | Typischer Hebel |
|---|---|---|
| **S1** Übervorsicht | `WEISS_NICHT`, obwohl der Kontext die Antwort trägt (auch: falsche Prämisse verweigert statt korrigiert) | Prompt Regel 3/4, Modell |
| **S2a** Sammelbeleg *(Modell)* | Aussagen korrekt, aber ein Beleg für mehrere Sätze oder Listenpunkte am Ende | Prompt Regel 2, Zitierbeispiel |
| **S2b** Fremdes Zitatformat *(Modell)* | `【1】`, `[1a]`, `[1.2]`, `[1(3a)]`, `[f]` — von Stufe 2 nicht erkannt | Prompt Regel 2, Erkennung in `confidence.py` |
| **S2c** Segmentierung *(Pipeline)* | korrekt belegt, aber Stufe 2 zerlegt falsch: Ordinalzahl «14.», «(z. B.», Listenpunkte unter 4 Wörtern, Einleitung mit Doppelpunkt | Satzzerlegung in `confidence.py` |
| **S2d** Lückensatz *(Pipeline)* | ein nach Regel 4 geforderter Satz «… nicht abgedeckt» zählt als unbelegt | Stufe 2 vs. Prompt Regel 4 |
| **S3** Echte Deckungslücke | Antwort enthält tatsächlich unbelegte oder falsche Aussagen | — Unterdrückung ist korrekt |
| **S4** Self-Check-Fehlurteil | Urteil falsch oder unlesbar | Self-Check-Prompt, Parser |
| **S5** Retrieval | erwartete Seite nicht im Kontext | ausserhalb Scope, nur notieren |
| **A** Artefakt | `length`, leere Antwort | Budget — Lauf ungültig |

**Kategorieübergreifend**

| Klasse | Bedeutung | Typischer Hebel |
|---|---|---|
| **P3** Sentinel im Fliesstext | `WEISS_NICHT` mitten in oder am Ende einer Antwort statt allein | Prompt Regel 3, Erkennung `_is_refusal` |
| **D** Gold-Erwartung strittig | Dataset-Erwartung fachlich falsch oder widersprüchlich zur Referenzantwort | fachliche Prüfung des Gold-Datasets (T-48) — nicht in dieser Optimierung ändern |

Daraus ergeben sich zwei Achsen je Modell, die die Leitthese sichtbar machen:

- **Urteilsfähigkeit** — Anteil inhaltlich richtiger Entscheide über das Entwicklungs-Set
  (P1, P2, S2a–d und D zählen als richtig; S1, S3, S4, F1, F2 als falsch).
- **Protokolltreue** — Anteil der Entscheide im geforderten Format
  (P1, P3, S2a, S2b zählen als Verstoss; S2c/S2d sind Fehler der Pipeline, nicht des Modells).

**Grenze beider Achsen:** Eingeordnet werden nur *Abweichungen*. Eine ausgelieferte
In-Corpus-Antwort, die wie erwartet durchkommt, wird nicht inhaltlich geprüft — ein Modell,
das viel ausliefert, erscheint deshalb eher zu gut. Die Achsen sind eine Untergrenze der
Fehler, kein vollständiges Qualitätsmass.

Die Zuordnung wird je Runde als Datei abgelegt (`labels/Rnn.csv`: Frage, Profil, Klasse,
Begründung in einem Satz). Eine LLM-gestützte Vorklassifikation ist erlaubt; die
Entscheidung trifft und verantwortet ein Mensch.

## 7. Überanpassung vermeiden — Holdout

Wer über mehrere Runden Prompts am selben Gold-Dataset feilt, optimiert auf genau diese
80 Fragen. Deshalb wird **vor R01** ein Holdout festgelegt und bis zur Schlussrunde nicht
ausgewertet:

- rund 30 % der Fragen, geschichtet nach Kategorie (`in_corpus` / `adversarial` /
  `out_of_corpus`) und Korpus (SKOS / AI Act / SAMW);
- die Aufteilung wird als Liste der Frage-IDs in `R00_Baseline.md` festgehalten
  und danach nicht mehr verändert;
- Prompt-Hypothesen dürfen nur mit Beispielen aus dem Entwicklungs-Set begründet werden.

Das CI-Gate (ADR-009) misst unverändert alle Fragen — der Holdout betrifft nur diese
Optimierung.

## 8. Modelle aufnehmen und weglassen

Jedes Modell hat einen **Steckbrief** (`Modelle.md`): Anbieter, Grösse, Architektur
(dicht/MoE), Denkmodus, Verfügbarkeit im Zielbetrieb, Profilparameter und die Beobachtungen
je Runde.

- **Weglassen**, wenn ein Modell auf der Testhardware nicht lauffähig ist, oder wenn es in
  zwei aufeinanderfolgenden Runden an Stufe 2 der Kriterien scheitert **und** die
  Einordnung zeigt, dass die Ursache nicht im Protokoll liegt. Ein Modell mit vielen P1-Fällen wird nicht weggelassen, bevor eine
  Prompt-Runde genau diese Schwäche adressiert hat — sonst verwirft man, was die Arbeit
  zeigen will.
- **Aufnehmen**, wenn eine Runde eine Eigenschaft als relevant erkennt (z. B. «Denkmodus
  schadet der Protokolltreue») und ein Modell diese Eigenschaft gezielt anders ausprägt.
  Die Aufnahme wird mit dieser Hypothese begründet.
- **Pausieren**, wenn ein Modell viel Rundenzeit bindet, als Produktivmodell kaum in Frage kommt,
  für eine *spätere* Runde aber gebraucht wird. Ein pausiertes Modell läuft nicht mit, bleibt
  im Steckbrief und wird mit Begründung wieder aufgenommen, sobald eine Runde seine
  Eigenschaft untersucht. Weglassen ist endgültig, Pausieren nicht.
- Die **Referenz** `openai` läuft in jeder Runde mit.

## 9. Ablauf einer Runde

1. **Hypothese** aus der vorherigen Runde, mit Verweis auf konkrete Fälle
   («S2 bei `ministral3-local`: 9 von 11 Coverage-Fällen bündeln die Fussnoten»).
2. **Genau eine Änderung** an einer Stellschraube (Abschnitt 4). Mehrere Änderungen nur,
   wenn sie unabhängige Stufen betreffen und getrennt auswertbar sind.
3. **Erwarteter Effekt** vor dem Lauf notieren — welche Kennzahl, welche Klasse, welche
   Richtung.
4. **Messen**: alle aktiven Profile je einmal, gleicher Git-Stand, `make eval`.
5. **Gültigkeit prüfen** (Abschnitt 5, Stufe 1). Ungültige Läufe werden korrigiert und
   wiederholt, nicht bewertet.
6. **Auswerten**: Kennzahlen (`eval.compare`), Einordnung der Abweichungen (Abschnitt 6),
   Vergleich zur Vorrunde.
7. **Entscheiden**: Änderung behalten oder verwerfen; Modelle weglassen oder aufnehmen —
   jeweils mit Verweis auf die Auswertung.
8. **Dokumentieren**: Runden-Dokument nach Vorlage, Commit mit den Rohzahlen-Berichten.
   Ein Runden-Dokument hat einen Abschnitt **«Kernaussage»**: ein Satz und eine Tabelle
   oder Grafik, die für die Schlusspräsentation taugt.

## 10. Ablage

```
EvalAnalysis/Optimierung/
  00_Vorgehen.md            dieses Dokument
  Modelle.md                Steckbriefe, laufend ergänzt
  Stellschrauben.md         Katalog: Hebel, Wirkung, Evidenz aus welcher Runde
  R00_Baseline.md           Ausgangslage, Holdout-Liste
  R01_<thema>.md            je Runde
  berichte/Rnn_Modellvergleich.md   generiert (eval.compare), nicht von Hand ändern
  labels/Rnn.csv            Einordnung der Abweichungen
  kennzahlen.csv            eine Zeile je Runde × Profil — Grundlage der Präsentation
  werkzeuge/                Auswertungsskripte je Runde, damit jede Zahl nachrechenbar ist
```

`kennzahlen.csv` ist die Datenbasis für die Schlusspräsentation: Verlauf der Kennzahlen
über die Runden, Urteilsfähigkeit gegen Protokolltreue je Modell, Wirkung je Stellschraube,
Laufzeiten auf der Testhardware als Grundlage für Zielhardware und Kosten.

## 11. Vorläufiger Rundenplan

Der Plan ist eine Erwartung, keine Verpflichtung — jede Runde begründet die nächste neu.

| Runde | Thema | Hypothese |
|---|---|---|
| R00 | Baseline | 5 Profile, gültige Messung, Einordnung aller Abweichungen, Holdout festlegen |
| R01 | Satzzerlegung in Stufe 2 | Stufe 2 zerlegte korrekt belegte Antworten falsch → **erledigt, übernommen** |
| R02 | Zitierformat: erziehen gegen tolerant lesen | Sammelbelege und fremde Formate senken die Coverage → **erledigt: Prompt übernommen, tolerantes Lesen verworfen** |
| R03 | Falsche Annahmen (Ausnahme in Regel 3) | Eine angehängte Ausnahme stellt widerlegte Annahmen richtig → **erledigt, verworfen (kein Effekt)** |
| R04 | Regeln 3 und 4 als eine Entscheidung | Verweigerung, Richtigstellung und Teilantwort als drei Fälle einer Entscheidung wirken, wo eine angehängte Ausnahme (R03) nichts bewegt — **erledigt, übernommen** (4 von 5 Profilen besser) |
| R05 | Self-Check-Prompt (neu, aus R04) | Stufe 3 prüft modellabhängig Vollständigkeit statt Deckung — der Prompt sagt beides. Eindeutig formuliert, fallen die S4-Fehlurteile weg, ohne dass Ungedecktes durchkommt |
| R06 | Generisch vs. modellspezifisch | Ein gemeinsamer Prompt erreicht nicht bei allen Modellen das Optimum — Mass für die «Nicht-Austauschbarkeit» |
| R07 | Schlussmessung | Bestes Setup je Modell auf dem Holdout; Entscheid Produktivmodell |

Zwei weitere Kandidaten aus R04, noch ohne Platz im Plan: **Belegdichte statt Belegzahl**
(Stufe 2b zählt, *ob* eine Nummer hinter einer Aussage steht, nicht *ob* sie stützt — eine
Verweigerung mit `[1][2][3][4][5]` erreicht Coverage 1,0) und eine **kürzere Fassung des
R04-Regelblocks** (länger heisst längere Antworten bei gleich vielen Belegen).

## 12. Offene technische Voraussetzungen

Vor R01 zu klären, jeweils als eigenes Issue:

1. **Prompt-Varianten in der Eval.** Heute darf ein Profil nur Modell und Budgets setzen
   (`tests/test_eval_profiles.py`); der Prompt steht fest im Code. Für Prompt-Runden
   braucht es eine nachvollziehbare Variante — entweder Prompt-Änderungen als Commit je
   Runde, oder ein Profilfeld, das dann in ADR-009 begründet wird. Modellspezifische Prompts
   im Betrieb wären ein Architekturentscheid (ADR-004: Provider über LiteLLM austauschbar).
2. **`eval.compare` um In-Corpus-Kennzahlen erweitern** (Halluzination, False-Suppression,
   Unterdrückungsgründe) und die Self-Check-Tabelle gegen mehrzeilige Urteile absichern
   (am 2026-09-14 bei `ministral3-local` umgebrochen).
3. **Holdout-Aufteilung** technisch abbilden (Filter nach Frage-IDs), ohne das CI-Gate zu
   verändern.
