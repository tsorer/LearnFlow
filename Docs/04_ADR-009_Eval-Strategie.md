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

- **Umfang Pilot:** Start **~80–100 Fragen**, mit dem Fachbereich (Stefan) erstellt/abgenommen. Jede In-Corpus-Frage hat erwartete **Quell-Chunk-IDs** und eine Referenzantwort.
- **Datenschutz/Versionierung:** Das Dataset speichert **Fragen + erwartete Quell-IDs/-Referenzen**, nicht den vollständigen Dokumenttext. Es lebt versioniert im Repo neben dem Code; sensible Volltext-Passagen bleiben in der (freigegebenen) Korpus-DB referenziert statt dupliziert.

### 2. Metriken & Akzeptanz-Gates

Drei Gruppen, abgeleitet aus den NFAs (Schwellen als Spike-kalibrierte Startwerte):

**A. Reliability (projektkritisch, deterministisch gemessen)**
- **Halluzinationsrate** auf In-Corpus: **= 0 %** (hartes Gate) — Antwort enthält keine nicht durch Quellen gedeckte Aussage.
- **Out-of-Corpus-Refusal-Rate:** **≥ 90 %** „Weiss ich nicht".
- **False-Suppression-Rate** (In-Corpus fälschlich unterdrückt): **≤ 15 %** Startwert — schützt die Nützlichkeit (Recall) gegen ein zu aggressives Fail-closed.

**B. Retrieval-Güte (deterministisch)**
- **Context-Recall@k** und **Context-Precision@k** gegen die erwarteten Quell-Chunk-IDs; **MRR/nDCG** für die Rangqualität. Primär für die Chunking-/Retrieval-Kalibrierung (ADR-007).

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

- **−** Erstellung des Gold-Datasets kostet **Fachbereichs-Zeit** (Stefan) — der teuerste, aber unverzichtbare Aufwand; ohne fachlich abgenommene Referenzen ist der Eval wertlos.
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

1. **Gold-Dataset mit dem Fachbereich aufbauen** (Stefan) — Voraussetzung für jeden Eval; vor Spike-Kalibrierung.
2. **Citation-Format finalisieren** (gemeinsam mit ADR-007/008), damit die deterministischen Checks maschinell parsen können.
3. **Akzeptanz-Schwellen** (False-Suppression ≤ 15 % etc.) nach dem ersten Kalibrierungslauf als „Accepted" bestätigen.
4. Repository-Ort und Zugriffsschutz für das Dataset festlegen (referenzierte Quell-IDs statt Volltext).

---

*Abhängigkeiten: ADR-007 (zu kalibrierende Retrieval-Parameter), ADR-008 (zu kalibrierende Konfidenz-Schwellen, deterministische Grounding-Checks), ADR-004 (LLM-as-Judge via Azure OpenAI EU), ADR-003 (`config` für Produktivkonfiguration im Eval) · Erfüllt: Verifizierbarkeit der Reliability-NFA, Testability-NFA · Speist sich aus: US-03 (Feedback-Loop)*
