# ADR-009: Eval-Strategie — Gold-Dataset + RAGAS/Custom-Harness als CI-Regressionsgate

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-31 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

ADR-007 (Chunking/Retrieval) und ADR-008 (Konfidenzpipeline) setzen zahlreiche Schwellen- und Strukturparameter (Chunk-Grösse, Overlap, Similarity-Schwelle, Citation-Coverage, Band-Grenzen, RRF-`k`, Top-`k`/`n`) — alle als **Hypothesen**, die „im Spike gegen ein Eval-Dataset kalibriert" werden müssen. Beide ADRs verweisen explizit auf eine **noch fehlende Eval-Strategie** als gemeinsame Abhängigkeit.

Der Grund ist grundsätzlich: **Man kann nicht tunen, was man nicht misst.** Die Reliability-NFA (Halluzinationsrate = 0 %, Out-of-Corpus ≥ 90 % „Weiss ich nicht") ist ohne ein reproduzierbares Messverfahren weder kalibrierbar noch verifizierbar — sie bliebe eine unbelegte Behauptung. Zugleich ist jede Parameteränderung teuer (Re-Indexierung, ADR-003/005), weshalb die Kalibrierung **früh und datenbasiert** erfolgen muss, nicht durch Bauchgefühl.

**Statistische Ehrlichkeit:** Eine endliche Eval-Menge kann „0 % Halluzination" nicht *beweisen* — sie kann es auf dem Dataset *demonstrieren* und eine obere Schranke schätzen. Echte Produktionssicherheit erfordert zusätzlich **laufendes Monitoring** (Nutzer-Feedback, US-03) als komplementäres Signal.

---

## Entscheidung

### 1. Gold-Eval-Dataset (versioniert, fachlich kuratiert)

Ein kuratiertes Frage-Antwort-Dataset als „Source of Truth" für alle Eval-Läufe:

| Kategorie | Anteil (Pilot) | Zweck |
|---|---|---|
| **In-Corpus** (beantwortbar) | ~60 % | Antwortqualität, Retrieval-Güte, Citation-Korrektheit |
| **Out-of-Corpus** (nicht beantwortbar) | ~25 % | „Weiss ich nicht"-Quote (≥ 90 %-Ziel) |
| **Grenzfälle / Adversarial** (teilweise gedeckt, mehrdeutig, suggestiv) | ~15 % | Fail-closed-Verhalten, False-Suppression |

- **Umfang Pilot:** Start **~80–100 Fragen**, gemeinsam mit dem Fachbereich erstellt und von ihm freigegeben. Jede In-Corpus-Frage hat eine Referenzantwort und eine erwartete **Quellreferenz** (Schema unten). Der Seed erreicht diesen Umfang über drei Korpora gemeinsam (SKOS-Richtlinien, EU AI Act, SAMW-Leitfaden), nicht je Korpus.
- **Fachliche Freigabe (verbindlich):** Das Dataset gilt erst als Source of Truth, wenn der Fachbereich Fragen, Referenzantworten und Quellreferenzen geprüft und freigegeben hat. Die Freigabe steht mit Datum im Kopf von `LearningCorpus/gold-eval-dataset.yaml`. Jede spätere inhaltliche Änderung — neue Frage, geänderte Referenzantwort oder Quellreferenz, geänderte `expected_refusal` — braucht eine erneute Freigabe. Ohne sie misst ein Eval-Lauf nur, ob die Pipeline mit den Annahmen der Entwicklung übereinstimmt, nicht ob die Antworten fachlich richtig sind.
- **Ablage:** **eine** Datei, `LearningCorpus/gold-eval-dataset.yaml`, mit einem `yaml.safe_load` ladbar. `src/backend/tests/test_gold_eval_dataset.py` prüft Schema und Konsistenz bei jedem CI-Lauf mit.
- **Datenschutz/Versionierung:** Das Dataset speichert **Fragen + Quellreferenzen**, nicht den vollständigen Dokumenttext. Es lebt versioniert im Repo neben dem Code — im PR reviewbar, mit `git blame`, wenn jemand eine Referenzantwort ändert — und kommt **nicht** in die DB: läge die Erwartung in derselben DB wie das geprüfte System, könnte ein Test grün werden, weil sich beide zusammen verschoben haben. Sensible Volltext-Passagen bleiben in der (freigegebenen) Korpus-DB referenziert statt dupliziert.

#### Quellreferenz-Schema

`expected_source` verweist auf **Dokument + Position**, nicht auf eine Chunk-ID:

```yaml
expected_source:
  pages: [46]
  locator: "Artikel 3 Nummer 3 — Begriffsbestimmung „Anbieter“"
```

- **Dokument:** kommt über `questions[].corpus` aus dem `corpora`-Block. Der nennt es **zweimal**, weil es zwei Dinge sind: `path` ist die Datei in `LearningCorpus/` (nur für den Test und um Seitenzahlen herzuleiten), `filename` die Upload-Identität in `documents` (eindeutiger Index über `(area, filename)`, T-15). Der Eval joint auf `filename`, und derselbe Name steht über `Citation.filename` unter der Antwort, die der Nutzer liest (US-01). Heute sind beide gleich — aber nur, solange der Korpus so hochgeladen wird. **Der Korpus ist unter genau diesen `filename` zu indexieren**; unter einem anderen Namen misst der Eval null Recall, ohne dass am Retrieval etwas falsch wäre.
- **Anker:** hängt am Content-Type und steht pro Korpus in `corpora[].anchor`. `parse_document` füllt genau eines der beiden Felder, nie beide: für `application/pdf` nur `page`, für `.docx` und `text/markdown` nur `heading`. Eine Frage trägt entsprechend `pages` **oder** `headings`.
- **`pages`:** 1-basierte PDF-Seiten, so wie der Parser sie zählt und wie `Citation.page` sie ausliefert — **nicht** die im Dokument gedruckte Seitenzahl (die kann abweichen, beim SAMW-Leitfaden um zwei). Eine Liste, weil Seitengrenzen harte Chunkgrenzen sind: eine Antwort über einen Seitenumbruch braucht beide Seiten, sonst deckelt das den Recall.
- **`locator`:** die Fundstelle in Prosa (Artikel/Kapitel/Randziffer). Nicht maschinell ausgewertet — sie trägt die fachliche Abnahme und erlaubt, die Seiten für eine neue Dokumentfassung neu herzuleiten.
- **Keine Chunk-IDs:** `chunks.id` ist ein UUID, und jede Neu-Indexierung vergibt neue — anderes `chunk_size`, anderes Embedding-Modell, Re-Upload desselben Dateinamens. Eingetragene IDs zeigten danach ins Leere, und das Eval-Gate würde rot, ohne dass sich an der Antwortqualität etwas geändert hätte.

### 2. Metriken & Akzeptanz-Gates

Drei Gruppen, abgeleitet aus den NFAs (Schwellen als Spike-kalibrierte Startwerte):

**A. Reliability (projektkritisch, deterministisch gemessen)**
- **Halluzinationsrate** auf In-Corpus (und den `adversarial`-Fragen mit `expected_refusal: false`): **= 0 %** (hartes Gate) — Antwort enthält keine nicht durch Quellen gedeckte Aussage. **Operationalisiert seit T-56** (`eval/metrics.py::check_hallucination`, Test in `eval/test_in_corpus_quality.py`): eine *ausgelieferte* Antwort gilt als halluziniert, wenn (H1) eine ihrer `[n]`-Referenzen auf keinen mitgelieferten Kontext-Chunk zeigt (`CitationDetail.valid` aus ADR-008 Stufe 2), oder (H2) keine der im Antworttext tatsächlich referenzierten Quellen (nicht: der gesamten mitgelieferten Kontextliste) aus dem für die Frage zugesagten Korpusdokument (`questions[].corpus`) stammt. Bewusst **kein LLM-Judge** in diesem Schnitt (Entscheid vom 2026-09-11, siehe Punkt 7 unten) — H1/H2 sind rein deterministisch und kosten keinen zusätzlichen Modellaufruf. Das misst eine mechanisch erkennbare Fehlerklasse ("Antwort stützt sich auf das falsche Dokument", die Klasse aus `EvalAnalysis/2026-09-10_Befunde.md` Punkt 4), nicht Faithfulness im RAGAS-Sinn — echte inhaltliche Deckung bliebe Aufgabe von Gruppe C.
- **Out-of-Corpus-Refusal-Rate:** **≥ 90 %** „Weiss ich nicht". Operationalisiert seit T-28 (`eval/test_out_of_corpus_refusal.py`).
- **False-Suppression-Rate** (In-Corpus fälschlich unterdrückt): **≤ 15 %** Startwert — schützt die Nützlichkeit (Recall) gegen ein zu aggressives Fail-closed. **Operationalisiert seit T-56**: Anteil der 45 `in_corpus`-Fragen mit `suppressed: true`. Die 13 `adversarial`-Fragen fliessen bewusst **nicht** in dieses Gate ein — eine Unterdrückung ist dort ein vertretbares Fail-closed-Ergebnis, kein Fehler; ihre beiden `expected_refusal: true`-Fragen werden stattdessen separat als Adversarial-Refusal ausgewiesen, ohne eigenes Gate (n=2 trägt keines).

**B. Retrieval-Güte (deterministisch)**
- **Context-Recall@k** und **Context-Precision@k** gegen die erwarteten Quellreferenzen; **MRR** für die Rangqualität (nDCG nicht umgesetzt — das Dataset trägt keine abgestuften Relevanzurteile, nur Treffer/kein Treffer, und würde nDCG auf MRR reduzieren). Ein Treffer zählt, wenn `chunk.document.filename == corpora[corpus].filename` und — je nach dessen `anchor` — `chunk.page` in `pages` bzw. `chunk.heading` in `headings` liegt. Primär für die Chunking-/Retrieval-Kalibrierung (ADR-007). **Operationalisiert seit T-56** (`eval/metrics.py::retrieval_metrics`), gegen alle 56 Fragen mit `expected_source` (45 `in_corpus` + 11 `adversarial`), in zwei Schnitten: top-k (alle Kandidaten der Fusion) und Kontext (nur `in_top_n`, was das LLM tatsächlich sah). Recall ist Seitendeckung (Anteil der erwarteten Seiten mit mindestens einem Treffer), nicht Chunk-Trefferquote — `pages` ist eine Liste, weil `chunking.py` Seitengrenzen zu harten Chunkgrenzen macht. Kein Gate: ADR-009 nennt für Gruppe B keinen Schwellenwert, das ist Eingabe für die Kalibrierung (T-57), nicht ihr Ergebnis.

**C. Antwortqualität (LLM-as-Judge)**
- **Faithfulness/Groundedness** (ist die Antwort durch den Kontext gedeckt?) und **Answer-Relevancy** — via RAGAS.

### 3. Harness & Tooling

- **RAGAS** für die RAG-spezifischen Metriken (Faithfulness, Answer-Relevancy, Context-Precision/Recall) — etabliert im Python-Ökosystem, fügt sich in den Stack.
- **Schlanke Custom-Schicht** für die *projektspezifischen, binären* Gates (Halluzination = 0 %, Refusal-Quote, False-Suppression) — diese sind zu wichtig, um sie einem Judge allein zu überlassen, und werden primär **deterministisch** über Citation-/Grounding-Checks (ADR-008, Stufe 2) gemessen.
- **LLM-as-Judge** läuft über **Azure OpenAI EU via LiteLLM** (ADR-004) — gleiche Compliance-Linie; Eval-Daten sind freigegebener Korpus. Als Judge ein starkes Modell (`gpt-4o`-Klasse), nicht das Antwort-Modell selbst.
- **Judge-Restrisiko:** LLM-Judges irren. Mitigation: binäre Halluzinations-Erkennung primär deterministisch (Citation-Coverage), Judge nur als Zusatzsignal; periodische **menschliche Stichprobe** auf einem Teil des Datasets.

### 4. Wann/wo der Eval läuft

- **Spike Woche 1 — Kalibrierungs-Loop:** Grid-/Sweep-Lauf über die ADR-007/008-Parameter; Ziel ist das Parameter-Set, das die Reliability-Gates erfüllt und gleichzeitig False-Suppression minimiert. Ergebnis fixiert die „Accepted"-Werte *vor* der Produktiv-Indexierung.
- **CI — Regressionsgate:** Bei jeder Änderung an der RAG-Pipeline läuft der Eval gegen das Gold-Dataset und die fixe Produktivkonfiguration. **Build bricht**, wenn die Halluzinationsrate > 0 % ist oder die Refusal-Quote unter die NFA fällt. (Testability-NFA, vgl. C4.)
- **Produktion — Monitoring:** Nutzer-Feedback (US-03) und unterdrückte/niedrig-konfidente Antworten werden geloggt und fliessen als reale Stichprobe zurück ins Gold-Dataset (kontinuierliche Erweiterung).

---

## Konsequenzen

### Positive Konsequenzen

- **+** Die Reliability-NFA wird von einer Behauptung zu einer **messbaren, im CI durchgesetzten** Eigenschaft — ohne Eval wäre „0 % Halluzination" nicht verifizierbar.
- **+** Ermöglicht überhaupt erst die datenbasierte Kalibrierung der ADR-007/008-Parameter, statt sie zu raten.
- **+** Regressionsgate verhindert, dass spätere Änderungen (Prompt, Modell, Chunking) die Reliability unbemerkt verschlechtern.
- **+** Deterministische Kern-Gates (Halluzination/Refusal) sind reproduzierbar und nicht von Judge-Schwankungen abhängig.
- **+** Compliance-konsistent: Judge-Aufrufe über Azure OpenAI EU; Dataset dupliziert keine sensiblen Volltexte.
- **+** Feedback-Loop (US-03) lässt das Dataset mit echten Nutzungsmustern wachsen.

### Negative Konsequenzen

- **−** Erstellung und Freigabe des Gold-Datasets kosten **Fachbereichs-Zeit** — der teuerste, aber unverzichtbare Aufwand; ohne fachlich freigegebene Referenzen ist der Eval wertlos.
- **−** LLM-as-Judge verursacht Token-Kosten pro CI-Lauf. Mitigation: festes, begrenztes Dataset (~100 Fragen); Judge nur für Gruppe C, nicht für die deterministischen Gates.
- **−** „0 % Halluzination" ist auf einem endlichen Dataset nur *demonstrierbar*, nicht beweisbar. Mitigation: explizit als Schranke kommuniziert + Produktions-Monitoring als Ergänzung.
- **−** Ein zu kleines/unrepräsentatives Dataset gibt falsche Sicherheit. Mitigation: bewusste Adversarial-/Grenzfall-Quote, kontinuierliche Erweiterung aus Feedback.
- **−** Judge-Fehlurteile (false positives/negatives) bei Gruppe C. Mitigation: deterministische Primärmetriken + menschliche Stichprobe.

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Keine formale Eval (nur manuelles Stichproben-Testing)** | Günstig, aber nicht reproduzierbar, nicht CI-fähig und nicht NFA-belegend. Macht die Reliability-NFA unprüfbar — inakzeptabel für das Kernversprechen. |
| **Reines LLM-as-Judge ohne deterministische Gates** | Bequem, aber die projektkritische 0 %-Halluzinationsmessung würde von Judge-Schwankungen abhängen. Deterministische Citation-/Grounding-Checks sind verlässlicher für das harte Gate. |
| **Vollständig eigenes Eval-Framework statt RAGAS** | Maximale Kontrolle, aber unnötiger Aufwand bei 360 h Umsetzungsbudget — RAGAS deckt die Standard-RAG-Metriken bereits ab. Nur die projektspezifischen Gates werden selbst gebaut. |
| **DeepEval / promptfoo / TruLens** | Valide Alternativen mit ähnlichem Funktionsumfang. RAGAS gewählt wegen Fokus auf RAG-Faithfulness-Metriken und guter Python/LiteLLM-Integration; Wechsel bliebe ohne Architekturfolgen möglich. |
| **Nur Offline-Eval, kein CI-Gate** | Würde Kalibrierung erlauben, aber spätere Regressionen nicht verhindern. Das CI-Gate ist der eigentliche Schutz über die Projektlaufzeit. |

---

## Offene Punkte / nächste Schritte

1. ~~Gold-Dataset fachlich freigeben~~ (T-48) — erledigt: Freigabe am 2026-09-01 erteilt, mit Datum im Kopf von `LearningCorpus/gold-eval-dataset.yaml` vermerkt. Damit ist die Voraussetzung für Eval-Läufe und die Spike-Kalibrierung erfüllt.
2. **Citation-Format finalisieren** (gemeinsam mit ADR-007/008), damit die deterministischen Checks maschinell parsen können. Offen dabei: `Citation` liefert heute nur `filename` und `page`, keinen `heading` — für ein `.docx`- oder `.md`-Dokument bleibt die Quellenangabe damit ohne Fundstelle.
3. ~~Harness prüft die Upload-Zusage~~ (T-28) — erledigt: `assert_corpus_is_indexed_async` (`eval/gold_dataset.py`) bricht laut ab, wenn ein `corpora[].filename` nicht oder nicht als `available` in `documents` steht, statt still 0 % Context-Recall zu melden. Seit T-56 auch vom In-Corpus-Test genutzt, nicht nur vom Refusal-Gate.
4. **Akzeptanz-Schwellen** (False-Suppression ≤ 15 % etc.) nach dem ersten Kalibrierungslauf als „Accepted" bestätigen. **Voraussetzung seit T-56 erfüllt** (Halluzinationsrate/False-Suppression sind jetzt messbar, siehe Gruppe A oben und `EvalAnalysis/`) — die eigentliche Kalibrierung ist T-57 (#125).
5. ~~Repository-Ort und Zugriffsschutz für das Dataset festlegen~~ — erledigt mit T-47: `LearningCorpus/gold-eval-dataset.yaml`, Quellreferenzen statt Volltext (Schema oben).
6. ~~Seitenzahlen für die SKOS-Einträge nachtragen~~ — erledigt mit T-48: alle 19 SKOS-Quellen tragen `pages`, jede aus einer wörtlichen Fundstelle im PDF hergeleitet statt aus einer Kapitelschätzung.
7. **LLM-Judge für Halluzination — bewusst zurückgestellt** (T-56, Entscheid 2026-09-11): Abschnitt 3 sieht den Judge als Zusatzsignal neben der deterministischen Prüfung vor ("primär deterministisch ... Judge nur als Zusatzsignal"). T-56 liefert nur die deterministische Seite (H1/H2, siehe Gruppe A) — ein Judge braucht ein zweites, stärkeres Modell (Abschnitt 3: "nicht das Antwort-Modell selbst"), eine neue Stelle in `eval/profiles.py` (die heute bewusst nur Modell und Zeitbudgets eines Profils erlaubt, nicht ein zweites Modell für einen anderen Zweck) und Kosten pro Lauf, die den Slice deutlich vergrössert hätten. Offen für einen eigenen späteren Schnitt.
8. **RAGAS (Gruppe C: Faithfulness, Answer-Relevancy) — nicht Teil von T-56.** Für die drei Gates aus Gruppe A/B ungebraucht (Abschnitt 3); ein eigener Ausbauschritt.

---

*Abhängigkeiten: ADR-007 (zu kalibrierende Retrieval-Parameter), ADR-008 (zu kalibrierende Konfidenz-Schwellen, deterministische Grounding-Checks), ADR-004 (LLM-as-Judge via Azure OpenAI EU), ADR-003 (`config` für Produktivkonfiguration im Eval) · Erfüllt: Verifizierbarkeit der Reliability-NFA, Testability-NFA · Speist sich aus: US-03 (Feedback-Loop)*
