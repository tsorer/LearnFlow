# ADR-008: Konfidenz- & Unterdrückungspipeline — Mehrstufige Defense-in-Depth, fail-closed

| Feld          | Inhalt                                |
| ------------- | ------------------------------------- |
| **Status**    | Accepted                              |
| **Datum**     | 2026-05-31 · aktualisiert 2026-06-03, 2026-08-16, 2026-08-20, 2026-08-22 |
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

Der **angezeigte** Konfidenzwert ist eine gewichtete Kombination aus Retrieval-Konfidenz (Stufe 1) und Citation-Coverage (Stufe 2); Gewichte im Code (siehe Nachtrag 2026-08-22). Mapping auf drei Bänder für die UI:

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

### Nachtrag 2026-08-20 — Wie Stufe 2 misst (T-19)

Stufe 2 ist oben als „Anteil belegter Antwort-Segmente" beschrieben. Was ein Segment ist und wann eine Referenz gilt, war damit nicht entschieden; ohne diese drei Festlegungen ist die Coverage keine reproduzierbare Zahl, sondern eine Auslegungsfrage. Sie stehen deshalb hier und nicht nur im Code (`app/services/confidence.py`).

1. **Segment = Satz oder Listenpunkt.** Gesplittet wird an `.!?` plus Leerraum, mit einer Liste deutscher Abkürzungen (`Art.`, `Abs.`, `z. B.`, `d. h.`, …), damit „gemäss Art. 5 Abs. 2" nicht in drei unbelegte Segmente zerfällt. Ein **Zeilenumbruch ist eine harte Segmentgrenze**: Reparaturen am Satzsplit wirken nur innerhalb einer Zeile, sonst zöge ein Listenpunkt die Referenz des nächsten an sich. Ein **einzelner Grossbuchstabe vor dem Punkt ist keine Abkürzung** — „Anhang A." beendet einen Satz; nur das Buchstabenpaar („z. B.", „i. S. v.") hält ihn zusammen. Beide Regeln sind fail-open-Fallen, die in der Umsetzung zuerst falsch lagen: die eine liess eine unbelegte Aussage von der Referenz des Folgesatzes mittragen, die andere entwertete jeden Aufzählungspunkt ausser dem ersten. Eine Referenz, die *hinter* dem Satzpunkt steht („Aussage. [1]"), wird der Aussage davor zugerechnet — sonst erzeugt ein verschobenes Leerzeichen eine Unterdrückung und einen falschen Treffer zugleich. Fragmente unter vier Wörtern (Überschrift, „Fazit:", nackter Aufzählungspunkt) sind Struktur, keine Aussage: sie zählen weder als belegt noch als unbelegt. Eine Antwort ganz ohne wertbares Segment kommt damit auf Coverage 0.0 und wird unterdrückt, solange `min_citation_coverage` über 0 liegt.

2. **Referenzformat.** Verbindlich ist `[n]` aus dem Grounding-Prompt, mehrfach als `[1][2]`. Die Komma-Form `[1, 2]` wird toleriert, weil jeder Index darin einzeln validiert wird und eine Unterdrückung wegen Zeichensetzung nichts gewinnt. Die Bereichsform `[1-3]` wird **nicht** aufgelöst: das hiesse, der Antwort Referenzen gutzuschreiben, die das Modell nie geschrieben hat. Nicht-numerische Klammern (`[sic]`) sind weder Referenz noch Erfindung und werden ignoriert.

   **Die Ziffernzahl ist keine Grenze** (Review zu PR #86). `n` ist ein Positionsindex in die Kontextliste, die der Prompt dem Modell übergibt — 1 bis `context_top_n`, im Default fünf. Es sind keine Dokumentnummern und keine Jahreszahlen, also ist jeder Wert ausserhalb dieses Bereichs gleich ungültig, unabhängig von seiner Länge. Eine auf drei Ziffern begrenzte Erkennung machte `[2026]` für die Prüfung unsichtbar — weder Referenz noch Erfindung, `valid` blieb `true`, die Antwort ging raus; dieselbe Aussage mit `[12]` wurde unterdrückt. Das teilte die fail-closed-Regel entlang der Stellenzahl der erfundenen Nummer und ist behoben. Der Preis ist derselbe wie bei der bekannten Grenze unten: schreibt ein Modell eine Jahreszahl als Fliesstext in eckige Klammern, wird die Antwort unterdrückt. Das ist die Fehlerrichtung, die dieses ADR trägt.

3. **Zwei Unterdrückungsgründe statt einem.** `citation_coverage` ist eine Schwellenfrage und über `min_citation_coverage` kalibrierbar. `citation_invalid` — eine Referenz auf einen nie gelieferten Chunk — ist keine: das ist ein Modellfehler, der unabhängig von jeder Schwelle unterdrückt, auch bei sonst perfekter Coverage. Eine erfundene Referenz belegt zudem ihr eigenes Segment nicht. Die Trennung ist im API-Vertrag sichtbar (`suppression_reason`), weil ein Betreiber die beiden Fälle verschieden behandeln muss: das eine kalibriert man, das andere untersucht man.

**Bekannte Grenze — eckige Zahlenklammern im Quelltext.** Stufe 2 kann eine zitierte `[12]` aus einem Dokument nicht von einer erfundenen Referenz unterscheiden; gäbe der Korpus solche Klammern her, würde eine korrekt belegte Antwort als `citation_invalid` unterdrückt. Der Fall wurde gegen den Korpus geprüft: 0 Treffer in EU AI Act und SAMW-Leitfaden (zusammen rund 945 000 Zeichen) sowie in den 206 geseedeten Chunks. Bewusst *nicht* entschärft — jede Lockerung („hohe Nummern sind wohl Zitate") entschuldigt genau die Halluzination, die Stufe 2 fangen soll, und die Fehlerrichtung ist Unterdrückung, die dieses ADR als akzeptablen Fehler führt. Kommt ein Dokument mit solcher Notation dazu, ist der Hebel der Grounding-Prompt (ADR-007/T-18) — dessen Änderung Review und Eval durchläuft — nicht eine Aufweichung der Prüfung.

**Bewusst in Kauf genommen:** Regel 4 des Grounding-Prompts verlangt, dass das Modell benennt, was der Kontext *nicht* abdeckt. Dieser Satz trägt konstruktionsgemäss keine Referenz und senkt die Coverage. Ihn auszunehmen ginge nur über eine Klassifikation des Satzinhalts — und damit wäre Stufe 2 nicht mehr deterministisch, was ihr Hauptargument gegenüber Stufe 3 ist. Beim Startwert 0.50 ist genug Abstand; die Kalibrierung (offener Punkt 1) misst es.

**Persistenz.** `answers.citation_coverage` bleibt `NULL`, wenn Stufe 2 nicht lief, und enthält sonst den gemessenen Wert — ein gespeichertes 0.0 wäre als „gemessen, nichts belegt" zu lesen und verfälschte die Kalibrierungsgrundlage. Im API-Feld `ConfidenceInfo.citation_coverage` fallen beide Fälle auf 0.0 zusammen, weil die Spec das Feld als nicht-nullable führt; unterscheidbar bleiben sie über `debug.stages`. Der von Stufe 2 zurückgehaltene Antworttext wird **nicht** gespeichert: `answer_text` ist, was die Pipeline ausgeliefert hat, und eine unterdrückte Antwort hat sie nicht.

### Nachtrag 2026-08-22 — Welche Keys über die Admin-API schreibbar sind (T-37, Issue #44)

Issue #44 liess offen, welche der elf `config`-Keys `PUT /admin/config` annehmen soll. Entschieden für T-37: schreibbar ist genau die Menge, die Migration `0012`s `CHECK`-Constraint bereits validiert — die beiden Konfidenz-Bänder plus die sechs Retrieval-Parameter aus ADR-007 (`similarity_threshold`, `min_retrieval_confidence`, `min_citation_coverage`, `retrieval_top_k`, `context_top_n`, `rrf_k`). Wer einen Key dort einträgt, bekommt Reader und Schreibpfad zusammen; die beiden hängen an derselben Konstante (`app/services/config.py`s `CONFIDENCE_THRESHOLD_KEYS`/`PIPELINE_KEYS`).

Zwei Keys bleiben bewusst draussen, über `GET` weiter sichtbar, nur nicht schreibbar:

- **`chunk_size`/`chunk_overlap`** (0007): eine Änderung wirkt erst nach vollständiger Re-Indexierung des Korpus — das widerspricht T-37s Akzeptanzkriterium „wirkt sofort ohne Neustart" wörtlich.
- **`stale_days`** (0004, US-06): weder ein Reader noch eine DB-seitige Wertregel existieren dafür bisher — es gibt nichts, wogegen eine Schreib-Validierung prüfen könnte.

Die Admin-Oberfläche (`ChatView.tsx`, `saveParams`) schickt `GET`s volle Antwort unverändert über `PUT` zurück, auch wenn nur ein Schwellenwert geändert wurde. Ein nicht schreibbarer Key ohne Wertänderung ist deshalb kein Fehler — nur eine echte Abweichung vom aktuellen Wert wird mit 422 abgelehnt. Ohne diese Ausnahme würde jede Speicherung allein durch die mitgeschickten nicht-schreibbaren Keys scheitern.
### Nachtrag 2026-08-22 — Komposit, Self-Check und die Reihenfolge (T-23, T-25, T-26)

Mit diesem Nachtrag sind alle Stufen umgesetzt. Drei Punkte, die das ADR offengelassen oder anders formuliert hatte, sind dabei entschieden worden.

**1. Die Komposit-Gewichte stehen im Code, nicht in `config`.** Oben stand „Gewichte in `config`"; das ist hiermit korrigiert. Der Grund ist derselbe, aus dem die Stufe-1-Gewichte schon dort stehen (`app/services/confidence.py`): Die `config`-Tabelle hält Schwellen, die eine Betreiberin gegen eine *feste* Skala nachjustiert. Eine Gewichtsänderung verschiebt die Skala selbst — jeder vorher geschriebene `answers.confidence_score` wäre mit jedem nachher geschriebenen nicht mehr vergleichbar, und genau diese Spalte ist die Kalibrierungsgrundlage aus ADR-009. Schwellen sind Betrieb, Gewichte sind Modell; das eine ändert man im laufenden Pilot, das andere mit Review und Eval. Startwerte: je 0.5, weil das die einzige Aufteilung ist, die nichts behauptet, was der Pilot noch nicht gemessen hat.

**Folge für die Kalibrierung:** `answers.confidence_score` enthält ab T-23 das Komposit statt der Retrieval-Konfidenz allein. Zeilen von vor diesem Stand messen etwas anderes und sind keine Vergleichsbasis — der offene Punkt 1 beginnt hier neu.

**2. Der Self-Check liefert ein Urteil, keine Zahl.** US-02 formuliert Stufe 3 als Prozentsatz („< 80 % → Eingeschränkt belegt, < 50 % → unterdrückt"). Das steht gegen die Abwägung weiter unten in diesem ADR, die die LLM-Selbsteinschätzung als *Mass* verwirft: Ein Modell, das seine eigene Belegquote auf 78 % beziffert, hat diese Zahl nicht gemessen, sondern erzeugt — und ein Gate darauf zu bauen heisst, genau der Instanz zu vertrauen, die Stufe 3 kontrollieren soll. Stufe 3 antwortet deshalb mit `GEDECKT` oder `NICHT_GEDECKT` plus den ungedeckten Aussagen im Klartext, also mit einer Behauptung, die ein Mensch nachprüfen kann. Alles, was nicht als eines der beiden Sentinels lesbar ist — leere Antwort, Prosa, eine selbst erfundene Schreibweise — gilt als **nicht** bestanden: eine Prüfung, die sich nicht auswerten lässt, hat nicht stattgefunden.

Die Bänder aus US-02 bleiben erhalten, kommen aber vom Komposit-Score über `confidence_threshold_high` / `_medium` — dort sind es kalibrierbare Zahlen statt Selbstauskünfte. Die Startwerte sind **0.75** und **0.45**, nicht die 80 % / 50 % aus dem ursprünglichen US-02-Text: jene bezogen sich auf eine LLM-Selbsteinschätzung und lassen sich nicht 1:1 auf ein anders gebildetes Mass übertragen. Beide sind Hypothesen bis zur Kalibrierung (offener Punkt 1). Die Akzeptanzkriterien in `Docs/02_Requirements.md` sind entsprechend umformuliert.

**3. Grenzband statt Grenzfall-Gefühl.** „Nahe der Schwelle" ist jetzt zwei `config`-Werte: `self_check_band_low` (0.45) und `self_check_band_high` (0.75). Halboffen — `low <= score < high` —, weil ein Score genau auf `high` bereits „klar hohe Konfidenz" ist und den zweiten Aufruf sparen soll. `low == high` ist damit ein leeres Band, also Stufe 3 bewusst abgeschaltet, so wie ein `similarity_threshold` von 0 Stufe 0 abschaltet. `low > high` wäre dasselbe *unbemerkt* und wird deshalb wie die Bandordnung aus dem Nachtrag 2026-08-16 in der Datenbank abgelehnt (Migration `0014`, aufgeschobener `CONSTRAINT TRIGGER`).

Die Startwerte sind bewusst **deckungsgleich mit den Konfidenz-Bändern**: `low` = `confidence_threshold_medium`, `high` = `confidence_threshold_high`. Das Grenzband ist damit exakt die `Mittel`-Spanne — jede Antwort, die ausgeliefert wird, aber nicht klar im oberen Band liegt, zahlt den Zusatzaufruf. Ein Review hat hier einen Startwert 0.50 gefunden, der eine Lücke [0.45, 0.50) erzeugte: Antworten darin wurden ausgeliefert *und* übersprangen Stufe 3 — ausgerechnet die am schwächsten belegten, die überhaupt noch durchkommen. Fail-open in genau der Richtung, die dieses ADR ausschliesst; korrigiert am 2026-08-25.

**Bekannte Grenze — die beiden Bandpaare sind nicht aneinander gekoppelt.** `self_check_band_high` unterhalb von `confidence_threshold_medium` schaltet Stufe 3 vollständig ab: Was darunter liegt, ist bereits unterdrückt, was darüber liegt, überspringt die Stufe. Kein Constraint fängt das. Bewusst so: die Kopplung zweier getrennter Key-Paare zwänge der generischen `config`-Tabelle mehr Struktur auf, als sie sonst trägt (vgl. Nachtrag 2026-08-16), und ein eng gestelltes Band ist eine legitime Kostenentscheidung. Sichtbar ist der Zustand pro Anfrage im Admin-Debug — die `self_check`-Stufe meldet dann bei *jedem* Score „ausserhalb des Grenzbands". Wer die Bänder verschiebt, prüft alle vier Werte zusammen; die Pilotstart-Checkliste führt sie deshalb als zwei Blöcke direkt untereinander.

**Reihenfolge (T-26).** Die Stufen laufen in genau der Folge, die der Entscheid vom 2026-05-20 in US-02 festhält: Quellenprüfung (Stufe 2) → Konfidenz (Komposit-Band) → Self-Check (Stufe 3). Jede Stufe kann unterdrücken, jede hat einen eigenen `suppression_reason` und einen eigenen standardisierten Text, weil der nächste sinnvolle Schritt sich unterscheidet: eine zu breite Frage schärft die Nutzerin selbst, eine erfundene Referenz kann sie nicht beheben. Dazu kommt je Grund ein `refinement_hint` (Requirements §71) — statisch aus dem Grund abgeleitet, ohne LLM-Aufruf: einen Provider ausgerechnet auf dem Pfad zu befragen, der existiert, weil die Pipeline einem Modell nicht getraut hat, wäre der falsche Ort dafür.

**Was ein Ausfall ist und was ein Urteil.** Ein nicht erreichbarer Provider bleibt in Stufe 3 ein 503, kein „Weiss ich nicht" — dieselbe Trennung wie bei der Generierung. „Die Prüfung hat ungedeckte Aussagen gefunden" ist eine Aussage über die Antwort, „der Provider antwortet nicht" eine über das System; einen Ausfall als Produktverhalten auszuliefern versteckt ihn.

**Persistenz.** `answers.self_check_passed` ist `NULL`, wenn Stufe 3 nicht lief — der Normalfall, weil sie nur im Grenzband feuert. Ein Default `false` würde jede übersprungene Prüfung wie eine gescheiterte aussehen lassen. Der Wortlaut des Urteils wird nicht gespeichert: er ist Material zum Debuggen einer einzelnen Anfrage und stünde sonst als generierte Prosa in einer Tabelle, deren `answer_text` bei unterdrückten Antworten bewusst `NULL` bleibt.

**Offen bleibt die Latenz.** Stufe 3 addiert einen zweiten Provider-Aufruf auf eine Anfrage, auf die ohne Streaming (ADR-002) jemand wartet. Das Grenzband begrenzt die *Häufigkeit*, nicht die Dauer im Einzelfall; ob die Performance-NFA (p95 ≤ 10 s) damit hält, misst T-22 und ist mit diesem Stand nicht gezeigt.

### Nachtrag 2026-08-26 — Warum die Quiz-Generierung nicht durch diese Pipeline läuft (T-33)

`POST /api/quiz/generate` ist der zweite LLM-Aufruf des Systems, der Text erzeugt, und er läuft **ohne** die Stufen 0 bis 3. Das ist kein Vergessen, sondern die Abgrenzung aus dem Kopf dieses ADR: alle vier Stufen messen eine *Antwort auf eine Frage* gegen die dafür *abgerufenen* Chunks. Bei der Generierung gibt es beides nicht — keine Nutzerfrage, kein Retrieval, also auch keinen Retrieval-Score, gegen den eine Schwelle etwas aussagen würde. Die Stufen hier nachzubauen hiesse, Zahlen zu erfinden, um sie anschliessend zu vergleichen.

Fail-closed bleibt es trotzdem, auf drei anderen Beinen:

**1. Der Mensch ist die Stufe.** `quiz_questions.status` steht per Spaltendefault auf `pending`, und für Lernende ist nur `approved` sichtbar (US-07). Eine generierte Frage ist ein Vorschlag, keine Veröffentlichung — anders als eine Antwort, die niemand vor der Auslieferung liest. Genau deshalb ist der Aufwand einer maschinellen Konfidenzprüfung hier nicht nötig: das Urteil, das die Pipeline im Antwortpfad ersetzen muss, wird ohnehin gefällt.

**2. Der Quellenbezug wird maschinell geprüft, nicht geglaubt.** Jede Frage nennt die Nummer des Abschnitts, aus dem sie stammt; eine Nummer, die es im Kontext nicht gibt, verwirft die Frage. Das ist derselbe Entscheid wie `citation_invalid` in Stufe 2 — eine erfundene Referenz ist ein Modellfehler, den keine Schwelle akzeptabel macht. Ebenso verworfen wird, was der Vertrag nicht hergibt: falsche Anzahl Optionen, eine richtige Antwort, die auf keine Option zeigt, doppelte Optionen.

**3. Ein Ausfall bleibt ein Ausfall.** Provider nicht erreichbar, Antwort nicht als die vereinbarte Struktur lesbar, oder keine einzige Frage überlebt die Prüfung: alle drei enden als 503, nicht als leeres Erfolgsergebnis. „Null Fragen erzeugt" wäre die getarnte Variante desselben Fehlers.

**Bekannte Grenze.** Ob eine Frage inhaltlich zu ihrer Passage passt, prüft nichts davon — das kann nur Stefan, und das Eval-Gate aus ADR-009 deckt diesen Pfad nicht ab (es misst Halluzination im Antwortpfad). Sollte sich im Pilot zeigen, dass zu viel Unbrauchbares in seiner Warteschlange landet, ist der nächste Hebel ein Self-Check über Frage und Quellen-Passage — die Stufe wäre wiederverwendbar, weil `run_self_check` bereits mit einem Text und einem Kontext arbeitet.
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
4. ~~**Zwischenstand der Pipeline (T-19, 2026-08-20):**~~ **erledigt (T-23/T-25/T-26, 2026-08-22)** —
   alle Stufen sind umgesetzt, der angezeigte `score` ist das Komposit, Stufe 3 läuft im
   Grenzband. Details im Nachtrag 2026-08-22. Im MVP werden weiterhin keine echten internen
   Dokumente verarbeitet (ADR-004).
5. **Latenz von Stufe 3 messen (T-22, #29):** Der zweite LLM-Aufruf im Grenzband ist gegen die
   Performance-NFA (p95 ≤ 10 s) nicht vermessen. Fällt er zu teuer aus, ist der Hebel das
   Grenzband, nicht das Abschalten der Stufe.

---

*Abhängigkeiten: ADR-007 (Retrieval-Gate als Stufe 0, Grounding-Prompt/Citations), ADR-004 (LLM-Aufruf für Self-Check, Provider-Portabilität), ADR-003 (`config`-Tabelle für Schwellen), ADR-005 (kein PyTorch-Re-Ranker/Klassifikator) · Erfüllt: Reliability-NFA, US-02 (Konfidenz-Anzeige)*
