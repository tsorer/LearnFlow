# Pipeline-Trace — eine Frage, zwei Formulierungen

Zwei Fragen, am 18.09.2026 gegen den laufenden Stack verfolgt, Stufe für Stufe. Gedacht als
Beispiel für die Abschlusspräsentation (Block 2).

| | Frage |
|---|---|
| **Q1** | Ich fahre innerorts 6 Km/h zu schnell wie hoch ist die Busse? |
| **Q2** | Ich wurde innerorts mit 6 zuschnell gebliztz was kostet mich das? |

Die Fragen sind **wörtlich** so gestellt, Tippfehler inklusive. Genau die machen einen Teil
des Befunds aus.

## Dateien

| Datei | Inhalt |
|---|---|
| `Q1.json`, `Q2.json` | **Rohdaten**: jede Zwischenstufe plus die vollständige API-Antwort mit `debug` |
| `Q1_trace.md`, `Q2_trace.md` | dieselben Daten lesbar: Zerlegung, beide Suchen (Top 20), Fusion, Kontext im Volltext, Prompts, Segmente, Stufen |
| `trace_pipeline.py` | erzeugt die JSONs, läuft im `api`-Container |
| `render_trace.py` | erzeugt die Markdown-Berichte aus den JSONs, läuft auf dem Host |

**Woher die Daten kommen.** Stufen, Prompts und Modellantworten stammen aus einem echten
`POST /query` als Admin, also aus derselben Debug-Ausgabe wie im Admin-Panel. Was die
Debug-Ausgabe nicht zeigt, zieht `trace_pipeline.py` mit denselben Service-Funktionen nach:
wie die Frage in Suchterme zerlegt wird, die rohen Dense- und Sparse-Listen vor der Fusion,
wie das Dokument gechunkt ist und wie Stufe 2 die Antwort in Segmente schneidet. Der
nachgezogene Kontext ist bei beiden Fragen **identisch** mit dem echten Lauf (gleiche Chunks,
gleiche Reihenfolge). **Produktivcode wurde nicht verändert.**

## Ergebnis auf einen Blick

Beide Fragen bekommen die richtige Antwort — **120 Franken**, OBV Anhang 1, Ziff. 303.1 b
(innerorts, 6–10 km/h), Seite 12. Der Weg dorthin ist aber ein anderer:

| | **Q1** — formal | **Q2** — umgangssprachlich |
|---|---|---|
| Suchterme nach der Zerlegung | `fahr · innerort · km · schnell · hoch · buss` | `wurd · innerort · zuschnell · gebliztz · kostet` |
| Sparse-Treffer im Korpus | 40 | **166** |
| Richtiger Chunk — Dense-Rang | **1** (Cosine 0,5236) | 2 (0,4353) |
| Richtiger Chunk — Sparse-Rang | 22 → **nicht in den Top 20** | 119 → nicht in den Top 20 |
| Richtiger Chunk — nach Fusion | **5 von 5** — letzter Kontextplatz | 3 von 5 |
| Kontext | 5× OBV | 3× OBV + **2× EU AI Act** |
| Stufe 1 (Schwelle 0,40) | 0,6021 | **0,4403** — 0,04 über der Unterdrückung |
| Stufe 2 Coverage | 1,0 | 1,0 |
| Komposit → Band | 0,8011 → **hoch** | 0,7202 → **mittel** |
| Self-Check | nicht nötig | **läuft** → `GEDECKT` |
| LLM-Aufrufe | 1 | 2 |

## Was das Beispiel zeigt

### 1 · Die Frage wird anders zerschnitten als das Dokument

Die Suchterme baut Python mit `re.findall(r"\w+")`, das Dokument zerlegt Postgres mit seinem
eigenen Parser. Die beiden sind sich nicht einig:

- **`Km/h`**: Python macht daraus `Km` und `h`, das `h` fliegt raus (zu kurz). Postgres speichert
  im Dokument aber **`km/h`** als ein Lexem. `km` trifft nie.
- **`6`**: fliegt als «zu kurz» raus. Postgres hätte `6` als Lexem, und die Tabelle enthält es.
- **`Busse`** wird zu `buss`. Im richtigen Chunk steht das Wort aber gar nicht: Die Tabelle
  nennt nur Beträge, die Einheit «Fr.» steht im Seitenkopf, und das Dokument selbst sagt
  «Ordnungsbussen» — als Kompositum `ordnungsbuss`, das `buss` nicht trifft.
- **`schnell`** trifft «Höchstgeschwindigkeit» nicht. Das kann nur die Dense-Suche überbrücken.

Von der ganzen Frage trifft im richtigen Chunk nur **`innerort`**. Das reicht für
Sparse-Rang 22 — zwei Plätze zu tief für die Top 20.

### 2 · Q1: Die Fusion drückt den besten Treffer auf den letzten Platz

Die Dense-Suche hat den richtigen Chunk auf **Platz 1**. Die Sparse-Suche hat ihn nicht in
ihren Top 20, er bekommt also nur einen RRF-Summanden (1/61). Vier Chunks, die beide
Suchen mittelmässig fanden, bekommen zwei Summanden und ziehen vorbei:

| Fusion | Dense | Sparse | RRF | Cosine |
|---|---|---|---|---|
| 1 | 5 | 4 | 0,031010 | 0,4778 |
| 2 | 8 | 9 | 0,029199 | 0,4640 |
| 3 | 18 | 2 | 0,028950 | 0,4373 |
| 4 | 19 | 10 | 0,026944 | 0,4361 |
| **5** | **1** | – | **0,016393** | **0,5236** |
| 6 | – | 1 | 0,016393 | 0,4281 |

Platz 5 ist der letzte Platz im Kontext. Ein Rang tiefer, und das Modell hätte die Antwort
nie gesehen. Mit Platz 6 teilt er sich sogar exakt denselben RRF-Wert, nur die höhere Cosine
entscheidet. **Das ist Befund 2 aus T-62 — «Rang-, kein Findungsproblem» — an einer einzelnen
Frage sichtbar.**

### 3 · Q2: Die Sparse-Suche holt Fremdmaterial in den Kontext

**`wurde`** steht nicht in der Stoppwortliste. Als `wurd` trifft es in jedem Rechtstext:
161 der 166 Sparse-Treffer kommen allein von diesem Wort. `zuschnell`, `gebliztz` und
`kostet` treffen im ganzen Korpus **nichts**. Die Sparse-Top-20 enthält darum **keinen einzigen
Chunk der OBV** — nur EU AI Act, SKOS und SAMW.

Die Fusion verzahnt dann beide Listen Platz um Platz. Zwei EU-AI-Act-Chunks landen im
Kontext, mit Cosine **0,16** und **0,21** — beide deutlich unter der Similarity-Schwelle von
0,35. Sie kommen trotzdem hinein, weil RRF Ränge verrechnet, nicht Scores. Das ist dieselbe
Kontamination über die Fusionsrangliste, die `EvalAnalysis/2026-09-11_In-Corpus-Befunde.md`
bei `SKOS-PRINZ-02` beschreibt.

Die Folgen, Stufe für Stufe:

- **Stufe 0** besteht (3 von 5 über der Schwelle).
- **Stufe 1** besteht knapp: Die zwei Fremd-Chunks drücken `mean` auf 0,336 und `density` auf 0,6.
  Ergebnis 0,4403 gegen 0,40.
- **Stufe 2**: Das Modell zitiert nur [3], den richtigen Chunk. Coverage 1,0.
- **Band mittel** → **Stufe 3 läuft** und urteilt `GEDECKT`.

Das Modell hat sich vom Fremdmaterial nicht irritieren lassen. Die Pipeline hat es aber
bemerkt: tieferes Band, eine zweite Prüfung.

### 4 · Was trägt — und was nicht

In **beiden** Fällen hat die Dense-Suche die Antwort gefunden. Die Sparse-Suche hat in Q1
den besten Treffer nach hinten gedrückt und in Q2 fremde Dokumente in den Kontext geholt.
Bei dieser Frage hat sie mehr geschadet als genützt.

Das ist **kein** Argument gegen die Hybrid-Suche. ADR-007 hat sie für exakte Fachbegriffe
eingeführt, und bei solchen Fragen ist sie im Vorteil. Es ist ein Argument dafür,
**zu messen, wo sie hilft**, statt es anzunehmen.

Und die Pipeline hat reagiert, wie sie sollte: Q2 hat nicht dieselbe Konfidenz bekommen wie
Q1, obwohl die Antwort dieselbe ist. Fail-closed heisst hier nicht «unterdrücken», sondern
**«genauer hinschauen, wenn die Grundlage dünner ist»**.

## Nebenbefund: Chunking

- Die OBV hat 82 Chunks, 38 bis 511 Tokens, Median 429. Das Ziel sind 512 Tokens.
- **Seitenwechsel sind harte Chunk-Grenzen.** Über eine Seitengrenze gibt es keine
  Überlappung, innerhalb einer Seite ungefähr einen Satz (Chunk 25 → 26: 139 Zeichen).
- Der richtige Chunk (26) beginnt mitten in Ziffer 302. Der Satzsplitter behandelt «302.» als
  Satzende, deshalb steht die Ziffernnummer am Ende von Chunk 25 und der Text dazu am Anfang
  von Chunk 26. Für diese Frage ist das harmlos: Ziffer 303.1 steht vollständig in Chunk 26,
  mit Überschrift und allen drei Zeilen der Tabelle.

## Grenzen

- **Zwei Fragen, je ein Lauf.** Das ist eine Demonstration, keine Messung. Das Retrieval ist
  deterministisch; die Modellantwort war es in T-62 trotz Temperatur 0 nicht immer.
- **Die OBV ist nicht Teil des Gold-Datasets.** Sie wurde am 18.09.2026 hochgeladen, das Eval
  weiss nichts von ihr.
- **Mögliche Korrekturen sind hier nicht gemessen**, nur naheliegend. Etwa: die Frage mit dem
  Postgres-Parser zerlegen statt mit Python-Regex, damit Frage und Dokument dieselben Lexeme
  haben (`km/h`, `6`); Hilfsverben wie «wurde» in die Stoppwortliste; ein Re-Ranker (P1 aus
  `Pipeline-Review.md`). Jede davon wäre vor einer Umsetzung gegen das Gold-Dataset zu messen.

## Neu erzeugen

```bash
docker cp trace_pipeline.py src-api-1:/tmp/trace_pipeline.py
MSYS_NO_PATHCONV=1 docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/trace_pipeline.py
MSYS_NO_PATHCONV=1 docker cp src-api-1:/tmp/pipeline-trace/Q1.json Q1.json
MSYS_NO_PATHCONV=1 docker cp src-api-1:/tmp/pipeline-trace/Q2.json Q2.json
python render_trace.py
```

Jeder Lauf ist ein echter `POST /query`. Er kostet zwei bis drei LLM-Aufrufe und schreibt eine
`answers`-Zeile, wie jede andere Frage auch. Die Modellantwort kann beim nächsten Lauf anders
ausfallen.
