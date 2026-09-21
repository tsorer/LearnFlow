# Block 2 · Technischer Aufbau — Notizen

Alles, was **nicht** auf den Folien steht: Sprechtext, Belege mit Fundstelle, Antworten auf
absehbare Nachfragen, offene Entscheide.

| | |
|---|---|
| Folien | [`Block2_Technischer-Aufbau.html`](Block2_Technischer-Aufbau.html) — 17 Folien |
| Gebaut von | [`build/build_block2_v3.py`](../../build/build_block2_v3.py) · `python build/build_block2_v3.py` |
| Themenentscheid dahinter | [`Block2_Themen.md`](Block2_Themen.md) |
| Rohdaten zum Beispiel | [`Pipeline-Trace/`](../../Pipeline-Trace/README.md) |
| Vorherige Fassung | [`Archive/`](../) — 19 Folien, nur Antwort-Pipeline |

## Die Idee dieses Blocks

Der Vorgänger war zu 100 % die Antwort-Pipeline. Diese Fassung stellt eine Landkarte davor:
**drei Wege durch dasselbe System** — Wissen hinein, Frage → Antwort, Fragen hinaus — und
schliesst mit den Belegen. Der rote Faden: *Maschine prüft die Antwort, Mensch prüft die
Frage, Messung prüft beides.* Er kommt auf Folie 2 und noch einmal auf Folie 17.

Zweites Muster, das sich durchzieht: Auf fast jeder Folie steht ein farbiger Kasten mit
**«Funktioniert gut»** (türkis), **«Funktioniert nicht»** (koralle) oder **«Das hat uns
überrascht»** (amber). Wer nur die Kästen liest, hat den Block verstanden.

## Ablauf und Zeit

| # | Folie | Weg | Zeit | Kasten |
|---|---|---|---|---|
| 1 | Vier Container. Eine Datenbank. | Landkarte | 0:40 | gut |
| 2 | Drei Wege durch dasselbe System | Landkarte | 0:25 | roter Faden |
| 3 | Bevor gefragt wird, muss gelesen werden | A | 0:35 | gut |
| 4 | Abschnitte, die an natürlichen Kanten enden | A | 0:25 | gut |
| 5 | Das Dokument bestimmt, wo geschnitten wird | A | 0:35 | **nicht** |
| 6 | Fünf Schritte, neun Arten «Weiss ich nicht» | B | 0:35 | Prinzip |
| 7 | Dieselbe Frage. Zwei Formulierungen. | B | 0:35 | gut |
| 8 | Zwei Zerleger, die sich nicht einig sind | B | 0:35 | **nicht** |
| 9 | Das Mischen rechnet mit Rängen, nicht mit Ähnlichkeiten | B | 0:40 | **nicht** (zweimal) |
| 10 | Dieselbe Antwort, nicht dasselbe Vertrauen | B | 0:40 | gut |
| 11 | Ein Beispiel ist eine Anekdote | B | 0:30 | überrascht |
| 12 | Das System stellt auch selbst Fragen | C | 0:35 | gut |
| 13 | Eine erfundene Quelle ist ein Fehler | C | 0:20 | Regel |
| 14 | Hier entscheidet kein Score | C | 0:30 | gut |
| 15 | Woher wir wissen, dass es hält | Belege | 0:35 | Prinzip |
| 16 | Der Massstab kann selbst falsch sein | Belege | 0:30 | **nicht** |
| 17 | Drei Wege, drei Prüfungen | — | 0:20 | überrascht |

**Summe: rund 9:05.** Retos Budget sind 6–7 Minuten — siehe Offene Entscheide, Punkt 1.

**Wenn es kürzer sein muss**, in dieser Reihenfolge streichen:
1. Folie 11 (Bilanz der Wortsuche) — die Aussage steht auch in Block 5. −0:30
2. Folie 13 (Provenienz-Regel) mündlich auf Folie 12 mitnehmen. −0:20
3. Folie 4 (Stückel-Regeln) auf einen Satz in Folie 3. −0:25
   → damit rund 7:50. Weiter zu kürzen geht nur noch auf Kosten der Verständlichkeit.

**Nicht streichen:** 2 (Landkarte der drei Wege), 6 (Pipeline-Überblick), 9 (Mischen),
14 (die menschliche Prüfung), 16 (Gold-Defekt).

---

## Folie für Folie

### 1 · Vier Container. Eine Datenbank.

**Sprechtext.** Modularer Monolith in Docker Compose, vier Container. Die API beantwortet
Fragen synchron, der Worker verarbeitet Dokumente im Hintergrund — die beiden teilen kein
Netz, der Worker ist von der API aus technisch nicht erreichbar.

**Der Punkt der Folie:** Postgres macht vier Jobs gleichzeitig — Tabellen, Vektoren
(pgvector, HNSW-Index), deutschen Volltext (tsvector, GIN-Index) und die Warteschlange
(pgqueuer). Kein Redis, keine zweite Datenbank.

**Beleg:** ADR-001/003/006, `Docs/05_C4-C2_Container.md`. Index-Definitionen direkt aus der
DB: `hnsw (embedding vector_cosine_ops) m=16, ef_construction=64` und `gin (tsv)`.

**Nachfrage «Warum kein Redis?»** Weil die Warteschlange dann ein zweites System mit eigenem
Betriebszustand wäre. pgqueuer arbeitet über LISTEN/NOTIFY in derselben Datenbank — ein
Backup, eine Transaktion. Der Preis: Die Queue skaliert nicht unabhängig von der Datenbank.
Für den Pilot ist das kein Thema.

### 2 · Drei Wege durch dasselbe System

**Sprechtext.** Alles, was wir gebaut haben, liegt auf einem von drei Wegen. Auf jedem
entscheidet jemand anderes über die Qualität. Diesen Satz brauche ich am Schluss wieder.

**Nicht sagen:** dass Weg C in der Demo vorkam — hängt davon ab, ob Reto das Quiz zeigt.

### 3 · Bevor gefragt wird, muss gelesen werden

**Sprechtext.** Stefan lädt hoch; die API nimmt die Datei an, legt sie in die Datenbank und
einen Job in die Warteschlange. Der Worker parst, stückelt, bettet ein, indexiert. Den
Fortschritt sieht Stefan in der Oberfläche — das war in der Demo die Statusanzeige.

**Der Punkt:** Die Herkunft entsteht beim Parsen. Ein Block ist eine PDF-Seite, ein
DOCX- oder Markdown-Absatz, und er trägt Seite und Überschrift mit. Nur deshalb kann der
Quellenlink später die Stelle im Originaldokument markieren.

**Zahlen (aus der laufenden Datenbank, 20.09.2026):** 4 Dokumente → 1017 Abschnitte.
EU AI Act 525 · SAMW-Leitfaden 210 · SKOS-Richtlinien 200 · OBV 82.

**Beleg:** `services/parsing.py`, `routers/documents.py` (10-MB-Limit, ADR-003).

### 4 · Abschnitte, die an natürlichen Kanten enden

**Sprechtext.** 512 Tokens Ziel, 64 Tokens Überlappung. Geschnitten wird zuerst an
Überschriften, dann Absätzen, Sätzen, Zeilen, Wörtern — jede feinere Stufe nur, wenn das
Stück immer noch zu lang ist.

**Der Punkt:** Gezählt wird mit `cl100k_base` — dem Tokenizer von `text-embedding-3-small`.
Sonst zählt man etwas anderes, als der Anbieter abschneidet.

**Beleg:** `services/chunking.py`, ADR-005/007. OBV-Zahlen aus `Pipeline-Trace/Q1.json`,
Abschnitt `10_chunking`: 82 Abschnitte, 38–511 Tokens, Median 429.

### 5 · Das Dokument bestimmt, wo geschnitten wird — «funktioniert nicht»

**Sprechtext.** Innerhalb einer Seite überlappen zwei Abschnitte etwa einen Satz, gemessen
139 Zeichen zwischen Abschnitt 25 und 26. Über einen Seitenwechsel hinweg: null Überlappung.

**Der Punkt:** Der Satzsplitter liest «302.» als Satzende. Deshalb steht die Ziffernnummer am
Ende von Abschnitt 25 und ihr Text am Anfang von 26. Für unsere Frage harmlos — Ziffer 303.1
steht vollständig in Abschnitt 26. Eine Tabelle über den Seitenumbruch wäre zerrissen.

**Ehrlich dazusagen:** Wir haben zuerst 0 Zeichen Überlappung gemessen und daraus geschlossen,
die Überlappung funktioniere gar nicht. Der Fehler lag an der Messung (tokengenauer Vergleich
statt normalisierter Text). Erst die zweite Messung zeigte das richtige Bild. Steht so in
`Pipeline-Trace/README.md`, Abschnitt «Nebenbefund: Chunking».

### 6 · Fünf Schritte, neun Arten «Weiss ich nicht»

**Sprechtext.** Suchen → Mischen → Vorprüfung → Antworten → Nachprüfen. Jede Stufe hat ihren
eigenen Grund zu unterdrücken; genau ein Weg führt zu einer Antwort. Nur zwei Schritte rufen
ein Sprachmodell: das Antworten und die Selbstprüfung. Die Suche braucht nur das
Embedding-Modell.

**Die neun Gründe** (Wire-Werte in `routers/query.py`): `retrieval_gate` ·
`retrieval_confidence` · `generation_refused` · `generation_truncated` · `citation_coverage` ·
`citation_invalid` · `confidence_band` · `self_check` · `configuration_error`. Dazu HTTP 503,
wenn der Anbieter ausfällt — ein Fehler, keine Notlösung.

**Korrigiert gegenüber der alten Fassung:** Die sprach von «acht Unterdrückungen». Es sind
neun; `configuration_error` war nicht mitgezählt.

### 7 · Dieselbe Frage. Zwei Formulierungen.

**Sprechtext.** Zwei echte Läufe gegen den Stack vom 18.09., wörtlich so gestellt, Tippfehler
inklusive. Die Antwort steht in der Ordnungsbussenverordnung, Anhang 1, Ziffer 303.1 b:
innerorts 6 bis 10 km/h zu schnell kostet 120 Franken.

**Der Punkt:** Die Bedeutungssuche findet beide — Q1 auf Platz 1 (Ähnlichkeit 0,5236), Q2 auf
Platz 2 (0,4353) von 1017 Abschnitten. «gebliztz» muss nirgends im Text stehen.

**Beleg:** `Pipeline-Trace/Q1.json` und `Q2.json`, Abschnitt `3_dense_top_k`.

### 8 · Zwei Zerleger, die sich nicht einig sind — «funktioniert nicht»

**Sprechtext.** Die Frage zerlegt Python mit einem Regex, das Dokument zerlegt Postgres mit
seinem eigenen Textparser. Im Detail:

- **`Km/h`** → Python macht `Km` und `h`; `h` fliegt als zu kurz raus. Postgres speichert im
  Dokument `km/h` als **ein** Lexem. `km` trifft nie.
- **`6`** fliegt als zu kurz raus — obwohl `6` im Dokument als Lexem existiert und in der
  Tabelle steht.
- **`Busse`** → `buss`. Das Dokument sagt «Ordnungsbussen» → `ordnungsbuss`, und im richtigen
  Abschnitt steht das Wort «Busse» gar nicht: Die Tabelle nennt nur Beträge, die Einheit «Fr.»
  steht im Seitenkopf.
- **`schnell`** trifft «Höchstgeschwindigkeit» nicht — das kann nur die Bedeutungssuche.

**Ergebnis:** Von der ganzen Frage trifft `innerort`. Sparse-Rang 22 bei Q1, Rang 119 bei Q2 —
beide ausserhalb der Top 20.

**Beleg:** `Q1.json` / `Q2.json`, Abschnitt `1_query_cutting` und `4_sparse_top_k`.

### 9 · Das Mischen rechnet mit Rängen — «funktioniert nicht, zweimal»

**Sprechtext.** Die Fusion (Reciprocal Rank Fusion) verrechnet Ränge, keine Ähnlichkeitswerte:
Wer in beiden Listen mittelmässig steht, bekommt zwei Summanden und schlägt den, der nur in
einer Liste Erster ist.

- **Q1:** Der Abschnitt mit der Antwort hat die höchste Ähnlichkeit der ganzen Liste (0,5236)
  und landet auf Platz 5 von 5 — dem letzten Kontextplatz. Mit Platz 6 teilt er sogar denselben
  RRF-Wert (1/61); nur die höhere Ähnlichkeit entscheidet.
- **Q2:** «wurde» steht nicht in der Stoppwortliste. Als `wurd` trifft es in jedem Rechtstext —
  161 von 166 Sparse-Treffern kommen allein von diesem Wort. In der Sparse-Top-20 ist **kein
  einziger** OBV-Abschnitt. Zwei EU-AI-Act-Abschnitte landen im Kontext, mit Ähnlichkeit 0,16
  und 0,21.

**Wichtig richtigzustellen, wenn gefragt wird:** Die Schwelle von 0,35 ist keine kaputte
Prüfung — sie prüft an einer anderen Stelle (Stufe 0 fragt, ob *mindestens einer* der fünf
Abschnitte darüber liegt). Die zwei fremden Abschnitte kommen in den Kontext, weil gemischt
wird, bevor Ähnlichkeiten wieder zählen. Das ist derselbe Effekt, den
`EvalAnalysis/2026-09-11_In-Corpus-Befunde.md` bei `SKOS-PRINZ-02` beschreibt.

**Das ist Befund 2 aus T-62** — «Rang-, kein Findungsproblem» — an einer einzelnen Frage
sichtbar: 13 von 15 Recall-Fehlern im Gold-Set sind Reihenfolgeprobleme, keine Fundprobleme.

### 10 · Dieselbe Antwort, nicht dasselbe Vertrauen

**Die Zahlen** (aus `7_stage1_confidence`, `8_stage2_result`, `9_composite`):

| | Q1 | Q2 |
|---|---|---|
| Stufe 1 = 0,5·top + 0,3·mittel + 0,2·Dichte | **0,6021** | **0,4403** (Schwelle 0,40) |
| davon mittlere Ähnlichkeit / Dichte | 0,4678 / 1,0 | 0,336 / 0,6 |
| Stufe 2 Belegdeckung | 1,0 | 1,0 |
| Komposit = 0,5·Fundlage + 0,5·Deckung | 0,8011 → **hoch** | 0,7202 → **mittel** |
| Stufe 3 Selbstprüfung | nicht nötig (über 0,75) | **läuft** → `GEDECKT` |
| Sprachmodell-Aufrufe | 1 | 2 |

**Der Punkt:** Fail-closed heisst hier nicht «unterdrücken», sondern «genauer hinschauen, wenn
die Grundlage dünner ist». Das Modell hat sich vom Fremdmaterial nicht irritieren lassen — die
Pipeline hat es trotzdem bemerkt.

**Wenn jemand fragt, wie knapp 0,44 ist:** vier Hundertstel über der Unterdrückung. Das ist
knapp, und es ist Absicht, dass es dann weiterläuft statt abzubrechen — unterdrückt würde eine
richtige Antwort.

### 11 · Ein Beispiel ist eine Anekdote — «das hat uns überrascht»

**Sprechtext.** Zweimal hat die Wortsuche hier geschadet. Aus zwei Fragen lässt sich nichts
schliessen, also nachgemessen: für 56 verankerte Gold-Fragen der Kontext mit beiden Suchen
gegen den Kontext nur mit der Bedeutungssuche.

**Ergebnis:** hilft 3× (AIA-RUECKRUF-01, AIA-LEITLINIEN-01, SAMW-HFG-INKRAFT-01), schadet 5×
(SKOS-GBL-01, SKOS-WOHN-01, SKOS-SANK-01, SKOS-KV-02, SKOS-KV-AUF-01), 48× kein Unterschied.
Trefferquote 0,766 → 0,772. Von 290 Kontext-Abschnitten stammen 8 aus einem fremden Dokument,
6 davon über die Wortsuche.

**Beleg:** `Pipeline-Trace/wortsuche_bilanz.py`, Messung vom 19.09.2026.

**Nicht überziehen:** Das ist kein Argument gegen die Hybrid-Suche. ADR-007 hat sie für exakte
Fachbegriffe und deutsche Komposita eingeführt, und dafür ist sie richtig — in unserem Korpus
ist dieser Fall nur selten. Es ist ein Argument dafür, zu messen statt anzunehmen.

**Überschneidung mit Block 4/5:** Christoph erzählt T-28 als Learning (Filtern schwacher
Abschnitte hätte Richtung Dense-only verschoben), in Block 5 steht «die Wortsuche kann
schaden» als Ausblick. Diese Folie ist die Messung dazu — abstimmen, wer was sagt.

### 12 · Das System stellt auch selbst Fragen

**Sprechtext.** Stefan löst aus, das System zieht zehn zufällige Abschnitte aus dem Bereich,
das Modell macht daraus in einem Aufruf fünf Multiple-Choice-Fragen mit vier Optionen und einer
Erklärung. Temperatur 0, kein Retry.

**Der Punkt:** Zehn Abschnitte für fünf Fragen — die Reserve ist Absicht. Mit genau fünf
müsste das Modell auch aus einem Inhaltsverzeichnis eine Frage pressen.

**Die gezeigte Frage ist echt**, aus der laufenden Datenbank (EU AI Act, freigegeben).

**Beleg:** `services/quiz.py` — der Docstring dort ist die ausführliche Fassung dieser Folie.

### 13 · Eine erfundene Quelle ist ein Fehler, kein Detail

**Sprechtext.** Jede Frage muss den nummerierten Abschnitt nennen, aus dem sie stammt. Nennt
sie eine Nummer, die es im Aufruf nicht gab, wird sie verworfen statt mit geratener Quelle
gespeichert. Dieselbe Regel wie `citation_invalid` im Antwortweg.

**Ausserdem verworfen:** keine vier Optionen, mehr als eine richtige Antwort, keine Erklärung.
Fünf Fragen sind das Soll; ein Lauf mit drei brauchbaren Fragen ist ein schlechter Lauf, kein
kürzeres Quiz (US-08).

### 14 · Hier entscheidet kein Score

**Sprechtext.** Generierte Fragen landen als `pending` und bleiben dort. Stefan gibt frei,
korrigiert den Text oder lehnt ab. Lernende ziehen fünf freigegebene Fragen zufällig.

**Der Punkt:** Auch die Sichtbarkeit ist fail-closed. Der Statusfilter kann die erlaubte Menge
nur verkleinern, nie vergrössern: Eine Lernende, die nach `pending` filtert, bekommt die leere
Schnittmenge — eine leere Seite, keinen 403 und keine unfreigegebene Frage.

**Der Kontrast, auf den es ankommt:** Lara wartet auf ihre Antwort, also muss die Maschine in
Sekunden prüfen. Auf eine Quizfrage wartet niemand — also prüft ein Mensch.

**Beleg:** `routers/quiz.py`, `visible_statuses()`; US-07/US-08.

### 15 · Woher wir wissen, dass es hält

**Sprechtext.** 80 Fragen mit bekannter Antwort, inklusive Seite. 45 stehen im Korpus,
22 nicht, 13 sind Fangfragen mit falscher Annahme. Alle laufen durch die echte Pipeline, drei
Grenzen müssen halten: keine erfundenen Belege (0 %), mindestens 90 % Ablehnung bei Fragen
ausserhalb des Korpus, höchstens 15 % fälschlich abgelehnte Fragen.

**Ehrlich zum Status:** Das Gate läuft heute manuell über `make eval`; als CI-Gate ist es noch
offen (T-53). Nicht verschweigen, wenn gefragt wird.

**Beleg:** ADR-009, `LearningCorpus/` (Gold-Dataset), `Docs/10_Kalibrierungsbericht.md`.

### 16 · Der Massstab kann selbst falsch sein — «funktioniert nicht»

**Sprechtext.** `SAMW-OOC-03` verlangt eine Ablehnung: Meldefristen stünden nicht im
Leitfaden. Sie stehen aber drin. Die Pipeline antwortete richtig und wurde als Fehler gezählt.

**Der Punkt:** Nach der Abnahme prüft niemand mehr gegen den Korpus. Ein falscher Eintrag
bestraft korrektes Verhalten dauerhaft und unbemerkt — und verschiebt am Ende die Schwellen in
die falsche Richtung. Das Gold-Dataset braucht dieselbe Prüfung wie der Code: gegen die Quelle.

**Beleg:** Issue #142; einer von drei gefundenen Fällen.

**Mit Frank absprechen** — er hat das Dataset abgenommen (T-48). Die Folie sagt nicht «Frank
hat schlecht gearbeitet», sondern «ein Datensatz altert wie Code». So auch sagen.

### 17 · Drei Wege, drei Prüfungen

**Sprechtext.** Wer prüft, hängt davon ab, wer wartet. Und das Überraschende zum Schluss: Die
heiklen Stellen lagen nie dort, wo wir sie vermutet haben — sondern zwischen zwei Bauteilen.
Zwischen Parser und Suche (Folie 8), zwischen Rang und Ähnlichkeit (Folie 9), zwischen
Gold-Dataset und Korpus (Folie 16).

**Übergabe an Frank (Block 3):** «Wie wir so gearbeitet haben, dass diese Stellen auffallen —
dazu Frank.»

---

## Bewusst nicht auf den Folien

| Thema | Warum nicht | Wenn gefragt wird |
|---|---|---|
| API-First, generierte Frontend-Typen, CI | ist Arbeitsweise → Franks Block | ADR-010: `openapi.yaml` ist der Vertrag, ein Test prüft Spec ↔ Code in beide Richtungen |
| Rollen, Rate-Limits, Datenminimierung | passt zu Frank (Security/Ethik, Modul 8) | drei Rollen, JWT; Limit pro **Konto**, nicht pro IP — die Pilotnutzer sitzen hinter einer NAT-Adresse |
| Laufzeit-Konfiguration ohne Deployment | nur relevant, wenn die Demo das Admin-Panel zeigt | Schwellen kommen pro Anfrage aus der DB. Fehlende Zeile → Default; kaputte Zeile → Fehler, nicht der lockerere Wert |
| Batch statt SSE (ADR-002) | erklärt nichts, was die Demo zeigte | bewusst: eine Antwort, wenn sie geprüft ist — kein Streaming einer Antwort, die Stufe 2 noch kippen kann |
| LiteLLM, Wechsel auf Azure OpenAI EU | gehört in den Ausblick (Block 5) | Provider ist Konfiguration, kein Code |
| Soft-Hyphen-Reparatur beim PDF-Parsen | zu klein für eine Folie | zwei pypdf-Versionen lesen denselben Trennstrich unterschiedlich; ohne Reparatur ist das Wort nicht suchbar |
| Kalibrierungs-Loop T-57, Messreihen T-62 | Block 5 | Schwellen maschinell suchen statt raten; T-62 liegt auf einem Branch |

## Offene Entscheide

1. **Zeit.** Der Block braucht rund 9 Minuten, Retos Gliederung sieht 6–7 vor. Entweder das
   Budget anpassen (die Demo davor ist mit 8–9 Minuten grosszügig bemessen) oder die drei
   Kürzungen oben umsetzen → 7:50. **Mit Reto klären.**
2. **Zeigt die Demo das Quiz?** Reto notiert «Quiz evtl. streichen». Wird es gestrichen, sind
   die Folien 12–14 die einzige Stelle, an der die Fragegenerierung überhaupt vorkommt — dann
   unbedingt behalten. Wird es gezeigt, kann Folie 12 kürzer ausfallen.
3. **Zeigt die Demo das Admin-Panel?** Wenn ja, einen Satz zur Laufzeit-Konfiguration
   ergänzen (Folie 1 oder 6).
4. **Abgrenzung zu Christoph (Block 4)** — T-28 und die Wortsuche. Er hat den Fall als
   Learning, ich habe die Messung. Wer sagt was?
5. **Abgrenzung zu Frank (Block 3)** — API-First und Security kommen bei ihm, nicht hier.
6. **Gold-Folie mit Frank** (Punkt 16) kurz vorbesprechen.
