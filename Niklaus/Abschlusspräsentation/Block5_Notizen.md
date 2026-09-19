# Block 5 · Fazit & Ausblick — Notizen

Arbeitsdatei für Niklaus. **Die Folien zeigen, diese Datei belegt.** Hier steht alles, was
nicht auf die Folien gehört, aber gebraucht wird: was ich sage, Antworten auf Nachfragen,
woher jede Zahl kommt, was noch offen ist.

| Datei | Inhalt |
|---|---|
| [`Block5_Fazit-Ausblick.html`](../../Artefakten/Abschlusspräsentation/Block5_Fazit-Ausblick.html) | **die Folien** (6), Layout von Christoph wie Block 2 |
| [`Pipeline-Trace/wortsuche_bilanz.py`](Pipeline-Trace/wortsuche_bilanz.py) | rechnet die Zahlen von Folie 3 nach |
| [`Block2_Notizen.md`](Block2_Notizen.md) | Block 2 — die Befunde, auf die dieser Block aufbaut |
| [`Inhalte_Abschlusspräsentation.md`](../../Artefakten/Abschlusspräsentation/Inhalte_Abschlusspräsentation.md) | Retos Gesamtgliederung |

**Rolle des Blocks:** Block 2 zeigt am Beispiel und im Eval, was wir gemessen haben — und dass
auch der Massstab selbst geprüft werden muss. Block 5 sagt, was daraus folgt: was wir gelernt
haben, was wir als Nächstes messen würden, was lokale Modelle heute können.

**Vorgabe aus Retos Gliederung:** keine zeitlichen Angaben, keine Deadlines, keine
Stundenzahlen. Offenes als bewusste Priorisierung framen, nicht als Rückstand.

---

## Offene Entscheide

1. **Zeit.** Retos Gliederung sieht 1–2 Minuten vor, das Deck braucht rund 3,5. Varianten:
   - **2 Min:** Folie 1 kürzer (nur Zielwert gegen Messung), Folien 2–4 als eine Geschichte
     (schadet → beides → Re-Ranker), P2–P4 in einem Satz, Folie 5 in einem Satz.
   - **3,5 Min:** alles — dann mit Reto klären, woher die Zeit kommt.
2. **T-65 (Gold-Dataset)** steht auf Folie 1 als bewusst offen. Das hängt an der Absprache mit
   Frank aus Block 2 (Offene Entscheide, Punkt 2).
3. **Christoph auf zwei Ungenauigkeiten hinweisen** (seine Learnings-Folie 2, T-28):
   - Seine Folie sagt, die zwei schwachen Wortsuche-Treffer (Cosine 0,24 / 0,21) «fanden exakte
     Fachbegriffe». Das steht so nicht im Issue #35. Dort sind es reine Wortsuche-Treffer, die
     Abschnitte mit 0,48 verdrängt haben; die Anfrage endete mit «Weiss ich nicht». Der Fall
     ist eher ein Beleg für «schadet» — dasselbe Muster wie unser Q2.
   - Der Kommentar in #35 begründet die Wortsuche mit T-50 (#102): «hochriskant war per
     Dense-Suche faktisch unauffindbar». T-50 zeigt das Gegenteil: «hochriskant» war per
     **Stichwortsuche** unauffindbar, weil das PDF die Wörter zerrissen hatte.
   - Wenn beide Blöcke das Thema streifen, sollten sie sich nicht widersprechen. Folie 3 hier
     liefert die gemessene Bilanz, auf die sich beide stützen können.

---

## Ablauf und Zeit

| # | Folie | Zeit | Kernaussage |
|---|---|---|---|
| 1 | Zielwerte sind Hypothesen | 0,7 Min | Ein «verfehlt» gegen eine unbestätigte Hypothese misst die Hypothese |
| 2 | Die Wortsuche kann schaden | 0,5 Min | Im Beispiel: 1 → 5 und 2 von 5 fremd |
| 3 | Hilft oder schadet? Beides. | 0,6 Min | 3 hilft, 5 schadet, 48 gleich — unterm Strich fast neutral |
| 4 | Was wir als Nächstes messen würden | 0,8 Min | P1–P4, nach gemessener Wirkung |
| 5 | Lokale Modelle | 0,7 Min | Machbar, noch nicht gut genug — zu vorsichtig ist auch ein Fehler |
| 6 | Schluss | 0,3 Min | Der Beleg, dass es hält, ist die eigentliche Arbeit |

---

## Folie für Folie

### 1 · Zielwerte sind Hypothesen, bis man sie kalibriert

**Überleitung aus Block 2:** «Wir haben gesehen, dass selbst das Gold-Dataset geprüft werden
muss. Dasselbe gilt für unsere Zielwerte.»

**Sagen:**
- Die 15 % für fälschlich unterdrückte Antworten stehen in ADR-009 ausdrücklich als Startwert,
  «nach dem ersten Kalibrierungslauf zu bestätigen». Dieser Lauf hat nie stattgefunden.
- Gemessen sind 22,2 % — von 31,1 % gesenkt, in vier Optimierungsrunden.
- Ein «verfehlt» gegen eine unbestätigte Hypothese misst die Hypothese, nicht die Pipeline.
- Bewusst offen, als Priorisierung: T-57 (Schwellen kalibrieren), T-65 (Gold-Dataset
  bereinigen), T-63/T-64 (Architektur-Hygiene, Konfiguration an einer Stelle).

**Falls gefragt:**
- *Warum 22,2 % und nicht die 37,8 % aus der In-Corpus-Messung?* Verschiedene Läufe und
  Code-Stände: 37,8 % (17 von 45) am 11.09., vor den T-62-Änderungen; 31,1 % in T-62 Runde R00;
  22,2 % nach Runde R04. Die Modellantworten sind auch bei Temperatur 0 nicht exakt
  reproduzierbar.
- *Was wurde in den vier Runden geändert?* R01: wie die Belegprüfung Sätze zerlegt (Ordnungs-
  zahlen, Abkürzungen, kurze Listenpunkte). R02: ein Beleg je Aussage im Prompt. R03: verworfen.
  R04: zwei Prompt-Regeln zu einer Entscheidung mit drei Fällen zusammengezogen.
- *Was ist T-57?* Parameter maschinell suchen statt raten. Die Such-Parameter lassen sich auf
  einem eingefrorenen Schnappschuss der Suchlisten offline durchrechnen, ohne Modellaufrufe. Für
  die Antwort-Schwellen braucht es echte Läufe — nur für die besten Kandidaten und dedupliziert
  nach Kontext. Ziel: das Parameter-Set, das die Gates erfüllt und am wenigsten fälschlich
  unterdrückt.
- *Warum ist das nötig?* Heute ändert, wer ändert, die Werte von Hand im Admin-Panel. Beim
  Eval-Lauf am 09.09. stand `min_citation_coverage` auf 0,28 statt 0,50 und
  `similarity_threshold` auf 0,41 statt 0,35 — handkalibriert, ohne Messgrundlage.
- *T-63/T-64?* T-63: Provider-Anbindung, API-Logging, Abhängigkeiten, Router-Kopplung. T-64:
  Konfigurationsschlüssel, Defaults und Grenzen an einer Stelle statt an fünf.

**Belege:** ADR-009 (Startwert) · `kennzahlen.csv` (openai R00 0,3111, R04 0,2222) ·
`In-Corpus-Befunde.md` §2 · T-62-Issue #136 (Runden) · GitHub #125 (T-57, inkl. der
handkalibrierten Werte), #142 (T-65), #137 (T-63), #138 (T-64).

### 2 · Die Wortsuche kann schaden

**Überleitung:** «Das Beispiel aus Block 2 hat noch etwas gezeigt, das wir so nicht erwartet
hatten.»

**Sagen:**
- Die Wortsuche haben wir für exakte Fachbegriffe eingebaut — zusammengesetzte Wörter,
  Abkürzungen (ADR-007).
- Im Beispiel hat sie geschadet. Q1: Die Bedeutungssuche hatte die Antwort auf Platz 1, nach dem
  Mischen blieb Platz 5 — knapp drin. Q2: Die Wortsuche fand praktisch nur «wurde» und brachte
  zwei Abschnitte aus dem EU AI Act in den Kontext.
- Ein Platz tiefer, und das Modell hätte die Antwort nie gesehen.
- Über 80 Fragen dasselbe Muster: 13 von 15 fehlende Quellen lagen in der Kandidatenliste, nur
  nicht unter den fünf.
- Learning: Zwei Suchen sind nicht automatisch besser als eine. Wo die Wortsuche hilft und wo
  sie schadet, muss gemessen werden.

**Überleitung zu Folie 3:** «Ist die Wortsuche also schlecht? Das haben wir nachgemessen.»

**Vorsicht:** Die 13 von 15 zeigen das Muster «gefunden, aber beim Schnitt auf fünf verloren»
— nicht, dass jedes Mal die Wortsuche schuld war. Auf der Folie steht deshalb «dasselbe
Muster». Die eigentliche Bilanz der Wortsuche ist Folie 3.

**Falls gefragt:**
- *Warum nicht einfach abschalten?* Siehe Folie 3: Dann fielen die drei Fälle weg, in denen sie
  hilft — darunter Abkürzungen wie «HFG».
- *Was würde helfen?* Ein Re-Ranker (Folie 4). Dazu kleinere Stellschrauben, alle **nicht
  gemessen**: die Frage mit dem Postgres-Parser zerlegen (dann bleiben «km/h» und «6» erhalten),
  Hilfsverben wie «wurde» als Füllwörter, ein besseres Volltext-Ranking — `ts_rank_cd` ist
  schwächer als BM25 (Pipeline-Review P6).
- *Was wäre passiert, wenn die Antwort rausgefallen wäre?* Das Modell hätte nur die anderen
  Abschnitte gesehen. Ob es dann «Weiss ich nicht» gesagt oder falsch geantwortet hätte, ist
  nicht gemessen.

**Belege:** `Pipeline-Trace/README.md` §2–§4 · `Pipeline-Review.md` §4 (13 von 15) und §8 P6
(T-62-Branch) · ADR-007.

### 3 · Hilft oder schadet? Beides.

**Sagen:**
- Wir haben nachgerechnet: Für jede der 56 Gold-Fragen mit bekannter Antwortseite — was hätte die
  Bedeutungssuche allein ins Modell gegeben, und was gibt die Mischung heute hinein?
- **3-mal hilft die Wortsuche.** Beispiel: «Humanforschungsgesetz (HFG)» — die Bedeutungssuche
  hat die Antwortseite nur auf Platz 7, die Wortsuche auf Platz 1. Genau dafür ist sie da:
  Abkürzungen, Fachbegriffe.
- **5-mal schadet sie.** Beispiel: «medizinische Grundversorgung» — die Bedeutungssuche hat die
  Antwortseite auf Platz 1, die Wortsuche findet sie nicht, die Seite fällt aus dem Kontext, und
  LearnFlow sagt «Weiss ich nicht». Was bei Q1 nur knapp gutging, ist hier passiert.
- **48-mal kein Unterschied.** Unterm Strich 77,2 % statt 76,6 % der Antwortseiten im Kontext —
  fast neutral.
- Learning: Die Wortsuche ist nicht schlecht, aber blindes Mischen nutzt nur die Hälfte ihres
  Werts. Überleitung zu Folie 4: der Re-Ranker.

**Falls gefragt:**
- *Wie genau gerechnet?* Das Retrieval ist deterministisch und läuft vor dem Modell. Aus den
  gespeicherten Rängen des Eval-Laufs lässt sich exakt ablesen, welche fünf Abschnitte die
  Bedeutungssuche allein geliefert hätte. Gezählt wird, ob die erwartete Seite darunter ist.
- *Was misst das nicht?* Wie die Antwort ohne Wortsuche ausgefallen wäre. Dafür bräuchte es einen
  echten Lauf mit abgeschalteter Wortsuche — das steht so auf der Folie.
- *Alle Fälle?* Hilft: AIA-RUECKRUF-01, AIA-LEITLINIEN-01 (trotzdem «Weiss ich nicht»),
  SAMW-HFG-INKRAFT-01. Schadet: SKOS-GBL-01, SKOS-WOHN-01, SKOS-SANK-01 (teilweise),
  SKOS-KV-02 und SKOS-KV-AUF-01 (ganz — beide endeten mit «Weiss ich nicht»). Auffällig: Alle
  fünf Schäden betreffen die SKOS-Richtlinien.
- *Fremdes Material?* 8 von 290 Kontext-Abschnitten stammen aus einem anderen Dokument als dem
  der Frage — 6 davon kamen über die Wortsuche.
- *Welcher Lauf?* Referenzmodell gpt-4o-mini, Runde R04 (16.09.), derselbe Lauf wie die
  Pipeline-Review. Korpus damals ohne die Ordnungsbussenverordnung.

**Belege:** `Pipeline-Trace/wortsuche_bilanz.py` (Ausgabe am 19.09. geprüft) · Rohdaten
`src/backend/eval/out/openai/in-corpus/2026-09-16T04-50-07Z/details.json` (lokal, gitignored) ·
`LearningCorpus/gold-eval-dataset.yaml`.

### 4 · Was wir als Nächstes messen würden

**Sagen:** Geordnet nach gemessener Wirkung, nicht nach Aufwand.
- **P1 Re-Ranker** zwischen Fusion und Gate — der grösste Hebel: +17 Prozentpunkte. Die Antwort
  auf «Beides»: Er bewertet die Kandidaten nach Inhalt, bevor auf fünf geschnitten wird, statt
  nur nach Platz. Ziel: den Nutzen der Wortsuche behalten, ohne dass sie verdrängt — **nicht
  gemessen**, das wäre die nächste Runde.
- **P2 Self-Check Satz für Satz** — die Frage «stützt Abschnitt [n] diesen Satz?» statt eines
  Gesamturteils.
- **P3 Stufe 0 und 1 ersetzen** — oder abschaffen und ehrlich dokumentieren.
- **P4 Embedding-Modell messen** — der einzige Hebel, der die Obergrenze selbst anhebt.

**Nur mündlich — P1 hat eine Architekturfrage im Rücken:** ADR-005 verbietet PyTorch im
Backend, ein klassischer Cross-Encoder fällt damit aus. Bleiben LLM-Re-Ranking über LiteLLM (ein
zusätzlicher Aufruf, offline vormessbar) oder ein gehosteter Re-Ranker (Cohere, Voyage) — ein
weiterer Anbieter und damit eine Datenschutzfrage vor dem Pilot. Kosten: Latenz; die Vorgabe
liegt bei p95 ≤ 10 s, gemessen sind 4,53 s.

**Falls gefragt:**
- *Was würde P3 fangen?* Die DSGVO/AI-Act-Verwechslung: Die Ähnlichkeit ist hoch, das Thema ein
  anderes. Keine Formregel im Prompt hat das je gefangen (R02, R04). Ein inhaltlicher
  Relevanzentscheid vor der Generierung — «decken diese fünf Abschnitte das Thema überhaupt
  ab?» — wäre der einzige Mechanismus in Sicht.
- *Warum P2?* Das Gesamturteil überfordert kleinere Modelle: ministral hat 8 von 16 Urteilen
  als `NICHT_GEDECKT` abgegeben — gegen genau eines bei allen anderen Modellen zusammen.
- *Warum P4?* `text-embedding-3-small` ist mehrsprachig, aber englischzentriert. Der Weg ist
  gebaut (T-42: Dimensionswechsel mit Reindexierung) — Kosten: eine Reindexierung, kein Umbau.
- *Weitere Punkte (P5, P6):* Die Frage wird heute gar nicht aufbereitet (kein Query-Rewriting);
  das Volltext-Ranking `ts_rank_cd` ist schwächer als BM25; der Kontext wird nicht in
  Dokumentreihenfolge gebaut.
- *Aus dem Beispiel:* Die Frage mit dem Postgres-Parser statt mit Python zerlegen (dann bleiben
  `km/h` und `6` erhalten) und Hilfsverben wie «wurde» als Stoppwörter. **Nicht gemessen** —
  vor einer Umsetzung gegen das Gold-Dataset prüfen.
- *Was wir bewusst nicht empfehlen:* Schwellen je Modell (gemessen und verworfen); MMR (der
  Kontext ist schon divers); die Coverage-Schwelle senken (bei 0,25 kämen sieben Antworten frei,
  zwei davon falsch).

**Belege:** `Pipeline-Review.md` §3–§8 (T-62-Branch) · `Stellschrauben.md` · ADR-005,
ADR-007 (freigehaltene Stelle für Re-Ranking) · `Pipeline-Trace/README.md`.

**Bewusst nicht verwendet:** die Literaturverweise in `Pipeline-Review.md` §8/§10 (Corrective
RAG, BGE-M3 usw.) — aus dem Gedächtnis zitiert, nicht verifiziert. Nur nennen, wenn vorher
geprüft.

### 5 · Lokale Modelle — «Machbar. Noch nicht gut genug.»

**Sagen:**
- Fünf Modelle, dieselbe Pipeline. Ein Modellwechsel ist kein Komponententausch: Das Modell muss
  das Ausgabeprotokoll bedienen — «WEISS_NICHT», Belege `[n]`, `GEDECKT`/`NICHT_GEDECKT`. Ein
  Modell kann richtig urteilen und trotzdem als Fehler zählen.
- Die interessante Zahl ist nicht die schlechte: Die beiden Modelle, die fremde Fragen am
  besten ablehnen (95,5 %), unterdrücken auch am meisten richtige. Zu vorsichtig ist auch ein
  Fehler.
- Und die Hardware ist der Filter.
- Für den Pilot ist Azure OpenAI EU gesetzt. Lokale Modelle sind die Stufe danach.

**Kurzvariante (ein Satz):** «Lokale Modelle können wir messen — zwei davon lehnen fremde
Fragen sogar besser ab als die Referenz, aber sie lehnen auch zu viele richtige ab, und das
grösste braucht auf unserer Hardware im Median fast eine Minute pro Antwort.»

**Falls gefragt:**
- *Beispiel, dass Modelle nicht austauschbar sind?* Runde R04: dieselbe Prompt-Änderung
  verbessert qwen3 (+9,1 pp gegenüber R03), gpt-oss (+4,6 pp gegenüber R03) und gemma4 (+4,6 pp
  gegenüber R01 — in R02/R03 pausiert), die Referenz hält 90,9 % — und ministral wird schlechter
  (fälschlich unterdrückt 31,1 % → 40,0 %). Ursache: längerer Regelblock → längere Antworten bei
  gleich vielen Belegen → mehr Antworten im Grenzband → und ministrals Self-Check liest den
  Auftrag als Vollständigkeits- statt Deckungsprüfung.
- *Die Referenz wurde dabei besser:* fälschlich unterdrückt 31,1 % → 22,2 %, Refusal unverändert.
- *Ein negatives Ergebnis:* R03 hängte die Behandlung falscher Annahmen als Ausnahme an die
  Verweigerungsregel. Kein Modell liest eine Ausnahme hinter «antworte ausschliesslich mit
  WEISS_NICHT». Verworfen und dokumentiert.
- *ministral «früher 100 %»?* In R00–R03 100 % Refusal, nach R04 95,5 %.
- *Was heisst «Zeit pro Antwort»?* Median der Generierungszeit in R04, ohne Self-Check.
- *Hardware:* Kein lokales Modell passt mit 16K-Kontext vollständig in 8 GB VRAM; die Modelle
  laufen teilweise auf der CPU.

**Belege:** `kennzahlen.csv` Runde R04 (`ooc_refusal_alle`, `false_suppression_alle`,
`gen_median_s`) · `EvalAnalysis/Optimierung/Modelle.md` (Steckbriefe, Testhardware) ·
`R04_Entscheidungsregel.md` · T-62-Issue #136 · ADR-004.

### 6 · Schluss — «Keine Antwort ohne Beleg. Das hält.»

**Sagen:** «Das Produktversprechen war: keine Antwort ohne Beleg. Das hält das System. Was wir
dazugelernt haben: Der Beleg dafür, dass es hält, ist die eigentliche Arbeit.»

Danach Übergabe an die Fragerunde.

---

## Referenzen

| Thema | Datei |
|---|---|
| Startwerte, Gates | `Docs/04_ADR-009_Eval-Strategie.md` |
| Provider, Azure-Wechsel | `Docs/04_ADR-004_LLM-Provider.md` · Pilotstart-Checkliste in `Ops/` |
| Embedding, kein PyTorch | `Docs/04_ADR-005_Embedding-Modell.md` |
| Re-Ranking-Stelle | `Docs/04_ADR-007_Chunking-Retrieval.md` |
| P1–P6, nicht empfohlen | `EvalAnalysis/Optimierung/Pipeline-Review.md` §8 (T-62-Branch) |
| Kennzahlen je Runde und Modell | `EvalAnalysis/Optimierung/kennzahlen.csv` (T-62-Branch) |
| Modell-Steckbriefe, Hardware | `EvalAnalysis/Optimierung/Modelle.md` (T-62-Branch) |
| False-Suppression 37,8 % | `EvalAnalysis/2026-09-11_In-Corpus-Befunde.md` |
| Offene Issues | GitHub #125 (T-57), #137 (T-63), #138 (T-64), #142 (T-65) |
