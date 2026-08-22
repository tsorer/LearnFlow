# ADR-008: Konfidenz- & Unterdrückungspipeline — Mehrstufige Defense-in-Depth, fail-closed

| Feld          | Inhalt                                |
| ------------- | ------------------------------------- |
| **Status**    | Accepted                              |
| **Datum**     | 2026-05-31 · aktualisiert 2026-06-03, 2026-08-16 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

Die Reliability-NFA (Halluzinationsrate = 0 %, bei Out-of-Corpus-Fragen ≥ 90 % „Weiss ich nicht") ist das zentrale Produktversprechen von LearnFlow: Lernende müssen den Antworten vertrauen können. US-02 verlangt zusätzlich, dass jede Antwort mit einer **Konfidenz-Angabe** versehen wird.

ADR-007 hat die *retrieval-seitige* Vorstufe entschieden (Schwellenwert-Gate: ohne ausreichend ähnlichen Chunk → kein LLM-Aufruf). Das allein genügt aber nicht: Auch wenn relevante Chunks gefunden werden, kann das LLM (a) über den Kontext hinaus halluzinieren, (b) Chunks falsch kombinieren oder (c) eine plausibel klingende, aber nicht belegte Antwort formulieren. Es braucht deshalb **nach** der Generierung weitere Prüfschichten und ein definiertes Konfidenz-Mass.

Diese „Konfidenz-Unterdrückungspipeline" wird im C4-Container-Diagramm und im Request-Flow vorausgesetzt (Quellenprüfung → Konfidenz → Self-Check, „< 50 % → unterdrückt"), war aber nie als Entscheidung dokumentiert.

Leitprinzip: **fail-closed**. Da die NFA 0 % Halluzination *über* hohem Recall priorisiert, wird im Zweifel unterdrückt („Weiss ich nicht") statt eine unsichere Antwort auszuliefern. Eine fälschlich unterdrückte Antwort ist ein akzeptabler Fehler; eine ausgelieferte Halluzination nicht.

**Abgrenzung:** ADR-007 = Chunking/Retrieval/Gate. ADR-008 = alles *nach* dem Retrieval-Gate (Konfidenz-Berechnung, Post-Generierungs-Prüfungen, User-Anzeige).

**Voraussetzung Batch-Response (ADR-002, aktualisiert 2026-06-03):** Die Pipeline ist sequenziell und fail-closed — alle Stufen müssen abgeschlossen sein, bevor die Antwort ausgeliefert wird. SSE-Streaming wurde deshalb bewusst verworfen (ADR-002). Der früher dokumentierte Konflikt «Streaming vs. Fail-Closed» ist damit aufgelöst.

---

## Entscheidung

Wir implementieren die Reliability als **mehrstufige Defense-in-Depth-Pipeline** im API Server. Jede Stufe kann unterdrücken; eine Antwort wird nur ausgeliefert, wenn alle Stufen passieren. Alle Schwellen liegen in der `config`-Tabelle (ADR-003) und sind **ohne Deployment** kalibrierbar.

### Stufe 0 — Retrieval-Gate *(aus ADR-007, vorgelagert)*

Kein Chunk über Similarity-Schwelle → sofort „Weiss ich nicht", kein LLM-Aufruf.

### Stufe 1 — Retrieval-Konfidenz (deterministisch, vor der Generierung)

Aus den Retrieval-Signalen wird ein **Retrieval-Konfidenz-Score** berechnet:

- maximale Similarity des Top-Chunks,
- mittlere Similarity der Top-`n`,
- Anzahl Chunks über Schwelle (Evidenz-Dichte).

Liegt der Score unter `min_retrieval_confidence` → „Weiss ich nicht" (kein LLM-Aufruf).

### Stufe 2 — Grounding-/Citation-Check (deterministisch, nach der Generierung)

Der Grounding-Prompt (ADR-007) zwingt das LLM, **jede Aussage mit einer Chunk-Referenz** zu belegen. Nach der Generierung wird deterministisch geprüft:

- Anteil belegter Antwort-Segmente (**Citation-Coverage**),
- Gültigkeit der Referenzen (zeigen sie auf tatsächlich gelieferte Chunks?).

Coverage unter `min_citation_coverage` (Startwert **50 %**) oder ungültige/erfundene Referenzen → **unterdrückt**.

### Stufe 3 — LLM-Self-Check (nur für Grenzfälle, kostenkontrolliert)

Für Antworten, deren Konfidenz **nahe der Schwelle** liegt, erfolgt **ein** zusätzlicher, günstiger LLM-Aufruf (Verifikations-Prompt): „Ist diese Antwort vollständig durch den bereitgestellten Kontext gedeckt? Welche Teile nicht?". Meldet der Self-Check ungedeckte Aussagen → unterdrückt. Antworten mit klar hoher Konfidenz überspringen diese Stufe (kein Token-Overhead im Normalfall).

### Komposit-Konfidenz & Anzeige (US-02)

Der **angezeigte** Konfidenzwert ist eine gewichtete Kombination aus Retrieval-Konfidenz (Stufe 1) und Citation-Coverage (Stufe 2); Gewichte in `config`. Mapping auf drei Bänder für die UI:

| Band                      | Bedeutung                  | UI                                                                             |
| ------------------------- | -------------------------- | ------------------------------------------------------------------------------ |
| **Hoch**                  | gut belegt, hohe Coverage  | Antwort + Quellen, grün                                                        |
| **Mittel**                | belegt, aber lückenhaft    | Antwort + Quellen + Hinweis, gelb                                              |
| **Niedrig / unterdrückt** | unter Schwelle / ungedeckt | „Weiss ich nicht" (+ optional nächstliegende Quellen, ohne generierten Inhalt) |

Unterdrückte Antworten liefern eine **standardisierte** „Weiss ich nicht"-Meldung — nie generierten Fließtext.

### Nachtrag 2026-08-16 — Wo die Schwellen validiert werden (Issue #73)

Der erste Reader (T-24) hat jeden unlesbaren oder invertierten `config`-Wert auf die Startwerte 0.75/0.45 zurückfallen lassen. Das ist in der Richtung, die zählt, **fail-open**: wer strenger stellen will und sich vertippt (deutsches Dezimalkomma `0,90`, Zahlendreher `0.09`, vertauschte Bänder), bekommt die *lockereren* Startwerte — bei einer Log-Warnung, die im Betrieb niemand liest. Zwei verschiedene Situationen wurden gleich behandelt:

| Situation                  | Bedeutung                          | Antwort                          |
| -------------------------- | ---------------------------------- | -------------------------------- |
| Zeile fehlt                | Niemand hat etwas anderes gewollt  | Default — dafür ist er da        |
| Zeile da, aber kaputt      | Jemand wollte etwas, es ging schief | Schreiben ablehnen, Lesen wirft  |

**Entscheid: Die Strenge liegt in der Datenbank, nicht im Anwendungscode.** Es gibt zwei Schreibpfade — die Admin-API (T-37) und direktes `psql`, das die Pilotstart-Checkliste ausdrücklich vorsieht. Eine Validierung in T-37 liefe am zweiten vorbei, deshalb sitzt sie eine Ebene tiefer und deckt beide ab (Migration `0009`):

1. **Pro Zeile: `CHECK`-Constraint** `ck_config_confidence_threshold_value` — für Keys `confidence_threshold_%` muss der Wert der Form `0.x` / `1.0` genügen (numerisch *und* im Bereich [0, 1] in einem Regex, weil PostgreSQL die Auswertungsreihenfolge innerhalb eines `AND` nicht garantiert und ein `value::numeric` sonst als Cast-Fehler statt als Constraint-Verletzung erscheinen kann).
2. **Über Zeilen hinweg: `CONSTRAINT TRIGGER`** `trg_config_confidence_band_order` — `medium <= high` betrifft zwei Zeilen, und `CHECK` ist in PostgreSQL zeilenweise und erlaubt keine Subqueries. `DEFERRABLE INITIALLY DEFERRED`, damit beide Werte in *einer* Transaktion in beliebiger Reihenfolge gesetzt werden können.
3. **Reader wirft** (`ConfigurationError`): ein vorhandener, aber nicht interpretierbarer Wert führt nicht mehr zu einem anderen, lockereren Wert. Ein **fehlender** Key fällt weiterhin auf den Default zurück — unverändert. Nach 1. + 2. ist der Wurf praktisch unerreichbar; er ist die Absicherung gegen einen Schreibpfad an der DB vorbei, nicht der Normalfall. Der Aufrufer (T-26) übersetzt ihn in „Weiss ich nicht", nicht in einen 500er — fail-closed bleibt fail-closed.

**Typisierte Spalten statt Key/Value** wurden verworfen: die `config`-Tabelle ist bewusst generisch (`stale_days`, `chunk_size`, `chunk_overlap`, künftig das Embedding-Modell aus T-42), und ein Umbau der Tabellenform zöge all das mit. Der Preis des gewählten Wegs ist, dass key-spezifische Regeln in einer generischen Tabelle stehen; der `CASE`-Block in `0009` ist deshalb um weitere Keys erweiterbar (T-42 braucht dieselbe Mechanik für `embedding_dimensions <= 2000`).

**Folge für den `psql`-Pfad:** Werden *beide* Bänder gesenkt, verletzt das erste `UPDATE` in psql-Autocommit die Invariante — jedes Statement ist dort seine eigene Transaktion, `DEFERRABLE` greift nicht. `Ops/07_Pilotstart-Checkliste.md` klammert die beiden `UPDATE`s deshalb in `BEGIN; … COMMIT;`.

Dieselbe Haltung gilt bereits für die Chunking-Parameter (`app/services/chunking.py`: ein unbrauchbares `chunk_size` wirft, statt still weiterzurechnen).

### Nachtrag 2026-08-22 — Welche Keys über die Admin-API schreibbar sind (T-37, Issue #44)

Issue #44 liess offen, welche der elf `config`-Keys `PUT /admin/config` annehmen soll. Entschieden für T-37: schreibbar ist genau die Menge, die Migration `0012`s `CHECK`-Constraint bereits validiert — die beiden Konfidenz-Bänder plus die sechs Retrieval-Parameter aus ADR-007 (`similarity_threshold`, `min_retrieval_confidence`, `min_citation_coverage`, `retrieval_top_k`, `context_top_n`, `rrf_k`). Wer einen Key dort einträgt, bekommt Reader und Schreibpfad zusammen; die beiden hängen an derselben Konstante (`app/services/config.py`s `CONFIDENCE_THRESHOLD_KEYS`/`PIPELINE_KEYS`).

Zwei Keys bleiben bewusst draussen, über `GET` weiter sichtbar, nur nicht schreibbar:

- **`chunk_size`/`chunk_overlap`** (0007): eine Änderung wirkt erst nach vollständiger Re-Indexierung des Korpus — das widerspricht T-37s Akzeptanzkriterium „wirkt sofort ohne Neustart" wörtlich.
- **`stale_days`** (0004, US-06): weder ein Reader noch eine DB-seitige Wertregel existieren dafür bisher — es gibt nichts, wogegen eine Schreib-Validierung prüfen könnte.

Die Admin-Oberfläche (`ChatView.tsx`, `saveParams`) schickt `GET`s volle Antwort unverändert über `PUT` zurück, auch wenn nur ein Schwellenwert geändert wurde. Ein nicht schreibbarer Key ohne Wertänderung ist deshalb kein Fehler — nur eine echte Abweichung vom aktuellen Wert wird mit 422 abgelehnt. Ohne diese Ausnahme würde jede Speicherung allein durch die mitgeschickten nicht-schreibbaren Keys scheitern.

---

## Konsequenzen

### Positive Konsequenzen

- **+** Defense-in-Depth: mehrere unabhängige Schichten — eine durchgerutschte Halluzination müsste Retrieval-Gate, Retrieval-Konfidenz, Citation-Check *und* Self-Check passieren. Das ist der Kern der 0 %-NFA.
- **+** **Fail-closed** als bewusste Auslegung: Precision vor Recall — passt zur Priorität „lieber keine Antwort als eine falsche".
- **+** Stufen 0–2 sind **deterministisch** (keine LLM-Abhängigkeit) → reproduzierbar, testbar und kostenlos; nur der Grenzfall (Stufe 3) kostet einen Zusatz-Token-Aufruf.
- **+** Alle Schwellen/Gewichte in der `config`-Tabelle → empirische Kalibrierung im Spike ohne Deployment (Maintainability-NFA).
- **+** US-02 direkt erfüllt: das Komposit-Mass ist die angezeigte Konfidenz, mit nachvollziehbarer Herleitung statt einer LLM-Selbsteinschätzung.
- **+** Provider-portabel: keine Abhängigkeit von providerspezifischen Token-Logprobs → funktioniert über LiteLLM mit Azure OpenAI EU *und* Ollama (ADR-004).

### Negative Konsequenzen

- **−** Höhere Latenz für Grenzfälle (Stufe 3 = zweiter LLM-Aufruf). Da kein Streaming mehr, wartet Lara auf die vollständige Antwort — Stufe 3 addiert direkt zur wahrgenommenen Wartezeit. Mitigation: nur nahe der Schwelle ausgelöst; bei klar hoher/niedriger Konfidenz übersprungen. Im Rahmen der Performance-NFA (≤ 10 s p95) zu validieren.
- **−** Fail-closed senkt den Recall: korrekte, aber knapp belegte Antworten werden evtl. fälschlich unterdrückt. Bewusst akzeptiert; über `config`-Schwellen justierbar.
- **−** Citation-Coverage misst *Beleg-Form*, nicht *inhaltliche Korrektheit* — ein LLM könnte korrekt zitieren und trotzdem falsch schlussfolgern. Mitigation: Stufe 3 (Self-Check) fängt einen Teil davon; Restrisiko über Eval messen.
- **−** Alle Startwerte (Coverage 50 %, Gewichte, Band-Grenzen) sind **Hypothesen** und ohne Kalibrierung gegen ein Eval-Dataset nicht NFA-garantierend. Abhängigkeit zur (noch offenen) Eval-Strategie.
- **−** Mehrere Stufen = mehr Code/Test-Oberfläche als ein simpler Schwellenwert. Mitigation: jede Stufe ist isoliert testbar (Testability-NFA, vgl. C4).

---

## Abgewogene Alternativen

| Alternative                                                           | Warum verworfen                                                                                                                                                                                                   |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Nur LLM-Selbsteinschätzung** („Wie sicher bist du? 0–100 %")        | Einfach, aber notorisch unzuverlässig — LLMs sind oft selbstsicher *und* falsch. Als alleiniges Mass ungeeignet für eine 0 %-Halluzinations-NFA. Fließt allenfalls als schwaches Zusatzsignal in Stufe 3 ein.     |
| **Token-Logprob-/Perplexity-basierte Konfidenz**                      | Token-Wahrscheinlichkeiten wären ein echtes Signal, sind aber providerabhängig und über die Chat-API uneinheitlich verfügbar — bricht die Provider-Portabilität (Azure ↔ Ollama via LiteLLM, ADR-004). Verworfen. |
| **Nur Schwellenwert-Gate (ADR-007), keine Post-Generierungs-Prüfung** | Günstig, aber lässt Halluzinationen *innerhalb* gefundener Chunks ungeprüft (falsche Kombination/Übergeneralisierung). Reicht für eine 0 %-NFA nicht.                                                             |
| **Self-Check für *jede* Antwort (immer zweiter LLM-Aufruf)**          | Maximale Sicherheit, aber verdoppelt Tokens/Latenz pro Anfrage. Verworfen zugunsten des kostenkontrollierten Grenzfall-Triggers (Stufe 3 nur nahe der Schwelle).                                                  |
| **Separater Klassifikator/Cross-Encoder als Faithfulness-Modell**     | Stärkste Faithfulness-Prüfung, holt aber PyTorch/ein Zusatzmodell zurück (gegen ADR-005) oder einen weiteren Provider. Post-MVP-Option; Schnittstelle bleibt offen.                                               |

---

## Offene Punkte / nächste Schritte

1. **Spike-Eval (Woche 1):** Schwellen (Retrieval-Konfidenz, Citation-Coverage, Band-Grenzen, Self-Check-Triggerbereich) gegen ein Eval-Dataset kalibrieren — inkl. Messung von Halluzinationsrate und „Weiss ich nicht"-Quote. Gemeinsame Abhängigkeit mit ADR-007 zur noch fehlenden **Eval-Strategie** (Kandidat für ein eigenes ADR/Spike-Deliverable).
2. ~~**Citation-Format festlegen:**~~ **erledigt (T-18, 2026-08-18)** — Referenzformat `[n]` und Verweigerungs-Sentinel `WEISS_NICHT` stehen im Grounding-Prompt-Kontrakt (ADR-007, Präzisierung T-18). `n` entspricht `Citation.index`, damit Stufe 2 deterministisch parsen kann.
3. Schwellen nach dem Spike als „Accepted" fixieren.
4. **Zwischenstand der Pipeline (T-18, 2026-08-18):** Umgesetzt sind Stufe 0 und Stufe 1;
   die Generierung läuft nur, wenn beide passieren. Stufe 2 (Citation-Check, T-19) und
   Stufe 3 (Self-Check, T-25) fehlen noch. Bis dahin bleibt `citation_coverage` 0.0, der
   angezeigte `score` ist die Retrieval-Konfidenz allein (das Komposit kommt mit T-23), und
   eine ausgelieferte Antwort ruht auf den beiden vorgelagerten Gates plus dem
   Grounding-Prompt. Das ist bewusst schwächer als der Endzustand dieses ADR — deshalb folgt
   T-19 unmittelbar auf T-18, und im MVP werden keine echten internen Dokumente verarbeitet
   (ADR-004).

---

*Abhängigkeiten: ADR-007 (Retrieval-Gate als Stufe 0, Grounding-Prompt/Citations), ADR-004 (LLM-Aufruf für Self-Check, Provider-Portabilität), ADR-003 (`config`-Tabelle für Schwellen), ADR-005 (kein PyTorch-Re-Ranker/Klassifikator) · Erfüllt: Reliability-NFA, US-02 (Konfidenz-Anzeige)*
