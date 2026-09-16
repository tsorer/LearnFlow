# Pipeline-Review — wie gut ist dieses RAG?

Eine Einschätzung der LearnFlow-Pipeline gegen Literatur und gängige Praxis, belegt mit den
Messungen aus `kennzahlen.csv` und drei zusätzlichen Auswertungen (`werkzeuge/retrieval_diagnose.py`,
`werkzeuge/recall_at_n.py`, `werkzeuge/gate_diagnose.py`). Stand 2026-09-16, Code-Stand `b7246f9`.

> **Zur Literatur:** Die genannten Arbeiten sind aus dem Gedächtnis zitiert, ohne
> Online-Recherche in dieser Sitzung. Autor, Jahr und Kernaussage sind belastbar; wer daraus
> in der Arbeit zitiert, prüft die genaue Fundstelle nach.

---

## 0. Kurzfassung

**Die Pipeline ist sicherheitsorientiert gebaut und hält, was sie in dieser Richtung
verspricht — sie bezahlt das mit Recall, und zwar mehr, als nötig wäre.**

| Zusage | Zielwert | gemessen (Referenz `gpt-4o-mini`, R04) | Urteil |
|---|---|---|---|
| Halluzinationsrate | 0 % | 0 % (0 von 41 ausgelieferten Antworten) | erfüllt, aber kleine Stichprobe |
| Out-of-Corpus-Refusal | ≥ 90 % | 90,9 % | knapp erfüllt |
| False-Suppression | ≤ 15 % | **22,2 %** | **verfehlt** |
| Context-Recall (top-5) | — | **0,772** | die eigentliche Obergrenze |

Die vier Befunde, die dahinterstehen:

1. **Die ersten beiden Stufen der Pipeline sind wirkungslos.** Stufe 0 und 1 haben über alle
   80 Fragen **keine einzige** blockiert — die Schwellen liegen unter der gesamten
   beobachteten Verteilung, und out-of-corpus-Fragen erreichen dieselben Werte wie
   beantwortbare.
2. **Die Retrieval-Lücke ist zu 87 % ein Rang-, kein Findungsproblem.** Die erwartete Seite
   liegt in 13 von 15 Fehlfällen in der Kandidatenliste, nur nicht in den fünf Chunks, die
   das Modell sieht. Genau dafür hat ADR-007 die Stelle für einen Re-Ranker freigelassen.
3. **Stufe 2 misst Belegform, nicht Belegbezug.** Eine Verweigerung in Prosa mit
   `[1][2][3][4][5]` erreicht Coverage 1,0; eine korrekte Antwort mit Sammelbeleg 0,33.
4. **Stufe 3 ist der einzige inhaltliche Filter der Pipeline — und modellabhängig.** Bei der
   Referenz greift sie in 16 Bandfällen genau einmal; bei `ministral-3` achtmal, davon
   fünfmal falsch.

Kurz: **die Pipeline ist konservativ an den Stufen, die nichts prüfen, und dünn an der
Stufe, die inhaltlich prüft.**

---

## 1. Datenbasis

80 Fragen des Gold-Datasets (45 `in_corpus`, 22 `out_of_corpus`, 13 `adversarial`) über zwei
Fachkorpora (SKOS-Richtlinien, EU AI Act) plus SAMW-Leitfaden. Fünf Modelle, sechs Runden
(R00–R04), je ein Lauf. Retrieval ist deterministisch und läuft vor dem Modell — die
Retrieval-Zahlen unten stammen deshalb aus einem Lauf und gelten für alle Profile.

**Statistische Ehrlichkeit vorab:** 0 von 41 Halluzinationen heisst nach der Dreierregel eine
obere 95-%-Schranke von rund **7 %**, nicht «null». Eine Frage der 22
Out-of-Corpus-Fragen sind 4,5 Prozentpunkte. Alle Aussagen unten, die sich auf einzelne
Fragen stützen, sind entsprechend zu lesen.

---

## 2. Was die Pipeline tut — und wo sie gegenüber der Literatur steht

| Baustein | Umsetzung hier | Stand der Praxis | Bewertung |
|---|---|---|---|
| Chunking | struktur-bewusst, 512 Token, 64 Overlap, Abkürzungsliste für juristisches Deutsch («Art.», «Abs.», «z. B.»), Seiten- und Überschriften-Anker | naives Fixed-Size-Splitting ist verbreitet; struktur-bewusst ist empfohlen, aber seltener umgesetzt | **über dem Durchschnitt** |
| Retrieval | hybrid dense (pgvector/HNSW, cosine) + sparse (Postgres FTS, deutsch, GIN), RRF `k=60` | Hybrid + RRF ist seit Cormack et al. (2009) der Standard; RRF fusioniert Ränge statt Scores und umgeht damit die Normalisierungsfrage | **Best Practice, korrekt implementiert** |
| Re-Ranking | **keins** (ADR-007 bewusst vertagt, Schnittstelle reserviert) | Cross-Encoder-Re-Ranking (Nogueira & Cho 2019; monoT5) ist der am besten belegte Einzelhebel nach dem Hybrid-Retrieval | **die grösste Lücke** |
| Query-Verarbeitung | Rohfrage als Embedding; sparse: Stoppwörter raus, max. 10 Terme, OR-verknüpft | Query-Rewriting, HyDE (Gao et al. 2022), Multi-Query/RAG-Fusion, Step-Back-Prompting | **fehlt vollständig** |
| Grounding-Prompt | Belegpflicht `[n]` je Aussage, Verweigerungs-Sentinel, Kontext als Material deklariert (Prompt-Injection) | Belege anzufordern ist üblich; sie **zu prüfen** ist es nicht | **stark** |
| Beleg-Prüfung | deterministisch: steht hinter jeder Aussage ein gültiges `[n]`? | ALCE (Gao et al. 2023) misst Citation Precision/Recall per **NLI-Entailment**, nicht per Formprüfung | **vorhanden, aber formal** |
| Abstention | fail-closed über vier Stufen, Komposit-Score, Bänder | Selective Prediction / Abstention ist ein eigenes Forschungsfeld; produktives RAG verzichtet meist ganz darauf | **deutlich über der Praxis** |
| Selbstprüfung | zweiter Aufruf desselben Modells, nur im Konfidenzband | Chain-of-Verification (Dhuliawala et al. 2023), LLM-as-a-Judge; Kostenbegrenzung durch ein Band ist eine kluge, eigene Idee | **gut, aber selbstbezogen** |
| Eval | 80-Fragen-Gold-Dataset, Holdout, Klassifikation aller Abweichungen, Recall/Precision/MRR | RAGAS (Es et al. 2023) und ähnliche Frameworks; ein fachlich abgenommenes Gold-Dataset mit Seitenankern ist selten | **die stärkste Seite des Projekts** |
| Kontextnutzung | 5 Chunks, Fusionsreihenfolge | «Lost in the Middle» (Liu et al. 2023): Positionseffekte in langen Kontexten | bei 5 Chunks unkritisch, relevant beim Vergrössern |

---

## 3. Befund 1 — Stufe 0 und 1 blockieren nichts

Retrieval-Konfidenz je Kategorie, alle 80 Fragen, Schwelle `min_retrieval_confidence = 0.4`:

| Kategorie | n | Min | Median | Max | unter der Schwelle |
|---|---|---|---|---|---|
| `in_corpus` | 45 | 0,52 | 0,73 | 0,83 | **0** |
| `adversarial` | 13 | 0,62 | 0,69 | 0,79 | **0** |
| `out_of_corpus` | 22 | 0,52 | 0,65 | 0,76 | **0** |

Top-1-Ähnlichkeit, Schwelle `similarity_threshold = 0.35`:

| Kategorie | Min | Median | Max |
|---|---|---|---|
| `in_corpus` | 0,50 | 0,69 | 0,82 |
| `out_of_corpus` | **0,46** | 0,60 | 0,71 |

**Von Stufe 0 und 1 wurde keine einzige Frage blockiert.** Beide Schwellen liegen unter dem
Minimum der gesamten beobachteten Verteilung, und die Verteilungen von «beantwortbar» und
«nicht beantwortbar» überlappen fast vollständig: eine Schwelle, die die 22
Out-of-Corpus-Fragen aussortiert, ohne in-corpus-Fragen mitzunehmen, **existiert nicht**.

Das ist kein Implementierungsfehler, sondern ein bekannter Effekt: Ein dichter Retriever
liefert immer etwas, und Cosinus-Ähnlichkeit eines Embedding-Modells ist ein schwacher
Out-of-Distribution-Detektor. Die Literatur zu adaptivem Retrieval (Self-RAG, Asai et al.
2023; Corrective RAG, Yan et al. 2024) baut genau deshalb einen *gelernten* oder
*modellgestützten* Relevanzentscheid ein statt eines Ähnlichkeitsschwellwerts.

**Konsequenzen für die Architektur:**

- Die vierstufige fail-closed-Kette von ADR-008 ist faktisch eine **zweistufige**: alles, was
  verweigert wird, verweigert das Modell selbst (Stufe 2a), die Coverage (2b) oder der
  Self-Check (3).
- Der Kalibrierungslauf aus T-57 (#139) fand `similarity_threshold = 0.2` und
  `min_retrieval_confidence = 0.2` als «optimal». Das ist erklärbar: an einem wirkungslosen
  Parameter ist jeder Wert gleich gut, der Optimierer bewegt ihn frei. Die beiden Werte
  sagen über die Pipeline nichts aus.
- Für die Arbeit ist das ein eigenständiges Ergebnis: **eine Schwelle, die nie greift, ist
  keine Sicherheitsstufe, sondern eine Annahme.**

---

## 4. Befund 2 — die Retrieval-Lücke ist ein Rangproblem

56 Fragen mit Seitenanker im Gold-Dataset:

| Grösse | Wert |
|---|---|
| Recall im Kontext (top-5, was das Modell sieht) | **0,772** |
| Recall in der Kandidatenliste (fusioniert, bis 40) | **0,945** |
| MRR über die Kandidaten | 0,698 |
| erwartete Seite(n) vollständig im Kontext | 40 von 56 |
| **Rangproblem** (in den Kandidaten, nicht im Kontext) | **13** |
| **Findungsproblem** (gar nicht gefunden) | **2** (`SAMW-JUGENDLICHE-01`, `AIA-ADV-04`) |

**13 von 15 Fehlfällen sind Rangfälle.** Die Information ist da, sie kommt nur nicht ins
Kontextfenster. Das ist die klassische Konstellation, für die Re-Ranking erfunden wurde: ein
günstiger Retriever holt breit, ein teurerer Scorer ordnet die Kandidaten neu.

Was ein grösseres Kontextfenster **ohne** Re-Ranker brächte:

| `context_top_n` | Recall | volle Deckung | Prompt-Zeichen (Median) |
|---|---|---|---|
| 3 | 0,731 | 39 von 56 | 4 642 |
| **5 (heute)** | **0,772** | **40 von 56** | **7 352** |
| 7 | 0,805 | 42 von 56 | 10 126 |
| 10 | 0,847 | 44 von 56 | 14 384 |
| 20 | 0,906 | 47 von 56 | 27 958 |

Von 5 auf 10 kostet die doppelte Prompt-Länge und bringt +7,5 Prozentpunkte Recall. Das ist
messbar und billig — **aber** R04 hat gezeigt, dass längere Prompts die Antworten länger
machen, ohne dass die Belege mitwachsen, und damit die Coverage senken. Ob der Recall-Gewinn
den Coverage-Verlust überwiegt, ist eine offene Frage und genau eine Runde wert.

**Redundanz ist nicht das Problem:** Der heutige Kontext enthält im Median 5 verschiedene
(Datei, Seite)-Kombinationen bei 5 Chunks. Eine Diversifizierung (MMR) würde hier nichts
gewinnen — die fünf Chunks stehen bereits auf fünf verschiedenen Seiten.

**Das Gold-Dataset erwartet meist eine Seite:** 44 der 56 Fragen haben genau einen
Seitenanker, 12 haben zwei bis vier. Der Recall-Verlust verteilt sich also auf echte
Fehlgriffe bei Einzelseiten-Fragen und Teiltreffer bei Mehrseiten-Fragen.

---

## 5. Befund 3 — Stufe 2 misst Form, nicht Stützung

Zwei Fälle aus R04, beide real gemessen:

- `qwen3` verweigert in Prosa: «Die Kontext-Abschnitte enthalten keine Angabe über den
  konkreten Betrag … `[1][2][3][4][5]`» → **Coverage 1,0**, ausgeliefert.
- `gpt-oss` beantwortet `AIA-ADV-02` inhaltlich korrekt, sammelt die Belege am Absatzende →
  **Coverage 0,33**, unterdrückt.

Stufe 2 fragt «steht hinter dieser Aussage eine gültige Nummer», nicht «stützt der Abschnitt
hinter der Nummer diese Aussage». Beide Fehler folgen direkt daraus.

Die Literatur zur Attribution löst das anders: ALCE (Gao et al. 2023) misst Citation Recall
und Precision, indem ein **NLI-Modell** prüft, ob der zitierte Abschnitt die Aussage
impliziert. Das ist die inhaltliche Variante genau dieser Stufe.

Dass diese Stufe formal misst, war lange **kein** Problem, weil halluzinierte Antworten
ohnehin schlecht belegt waren — Stufe 2 filterte nebenbei Inhalte mit. R02 hat den Prompt
verbessert, die Formtreue ist gestiegen, und damit ist dieser Nebeneffekt weggefallen: seither
sind auch falsche Antworten sauber zitiert (der DSGVO/AI-Act-Fall mit Coverage 1,0). Die
inhaltliche Prüfung hängt seitdem allein an Stufe 3.

---

## 6. Befund 4 — Stufe 3 trägt die ganze inhaltliche Last und ist modellabhängig

| Profil | Stufe 3 gelaufen (von 58) | GEDECKT | NICHT_GEDECKT |
|---|---|---|---|
| `openai` | 16 | 15 | **1** |
| `qwen3-local` | 4 | 4 | 0 |
| `gpt-oss-local` | 12 | 12 | 0 |
| `ministral3-local` | 16 | 8 | **8** |
| `gemma4-local` | 5 | 5 | 0 |

Bei der Referenz greift der einzige inhaltliche Filter der Pipeline **einmal in 58 Fragen**.
Bei `ministral` achtmal, davon fünf nachweisbare Fehlurteile (das Modell prüft
Vollständigkeit statt Deckung — R04, 4.3).

Dazu kommt die strukturelle Schwäche: Stufe 3 fragt **dasselbe Modell**, das die Antwort
geschrieben hat. Die Literatur zu LLM-as-a-Judge ist an diesem Punkt einig, dass
Selbstbewertung zu Selbstbestätigung neigt; Chain-of-Verification (Dhuliawala et al. 2023)
arbeitet deshalb mit zerlegten Einzelfragen statt einem Gesamturteil.

---

## 7. Was diese Pipeline besser macht als übliche Praxis

Damit die Kritik oben nicht den Eindruck erweckt, das sei eine schwache Pipeline — vier
Dinge, die in produktivem RAG selten sind:

1. **Belege werden geprüft, nicht nur angefordert.** Der Normalfall in der Praxis ist ein
   Prompt, der um Quellenangaben bittet, und niemand schaut nach.
2. **Verweigerung ist ein Produktverhalten, kein Fehlerfall.** Sentinel, Komposit-Score,
   Bänder, eigene Meldungen je Unterdrückungsgrund — und ein Eval, das Übervorsicht als
   eigene Kennzahl misst statt sie als Sicherheit zu verbuchen.
3. **Das Gold-Dataset hat Seitenanker**, weshalb Recall überhaupt messbar ist. Ohne das wäre
   Befund 2 nicht formulierbar, und die meisten Projekte können ihn deshalb nicht formulieren.
4. **Prompt-Injection ist adressiert** (Kontext ausdrücklich als Material deklariert), und
   die Trennung Retrieval / Konfidenz / Generierung ist im Code sichtbar statt nur im
   Diagramm.

Dazu kommt der methodische Teil, der für die Arbeit zählt: rundenbasierte Optimierung mit
Hypothese, einer Stellschraube, Holdout, Klassifikation jeder Abweichung und dokumentierten
**negativen** Ergebnissen (R02b, R03).

---

## 8. Was die Pipeline verbessern würde — nach gemessener Wirkung geordnet

### P1 — Re-Ranker zwischen Fusion und Gate

**Evidenz:** 13 der 15 Recall-Fehlfälle sind Rangfälle; Recall 0,772 (Kontext) gegen 0,945
(Kandidaten). Der Kopfraum ist mit **+17 Prozentpunkten** der grösste einzelne Hebel der
ganzen Pipeline.

**Warum es hier passt:** ADR-007 hat die Stelle ausdrücklich freigehalten («ein
Re-Ranking-Schritt zwischen Fusion und Gate ohne Architekturumbau»), und `retrieval.py` gibt
`candidates` und `context` bereits getrennt zurück.

**Die Architekturfrage:** ADR-005 verbietet PyTorch im Backend, ein klassischer
Cross-Encoder fiele damit aus. Zwei Wege bleiben:

- **LLM-Re-Ranking über LiteLLM** — ein billiges Modell bewertet die 20 Kandidaten gegen die
  Frage. Ein zusätzlicher Aufruf je Anfrage, respektiert ADR-004 und ADR-005, und ist offline
  auf den gespeicherten Kandidatenlisten vormessbar, bevor eine Zeile Produktivcode entsteht.
- **Gehosteter Re-Ranker** (Cohere Rerank, Voyage) — stärker, aber ein weiterer Anbieter und
  damit eine Datenschutzfrage vor dem Pilotstart.

**Kosten:** Latenz. Die Performance-NFA liegt bei p95 ≤ 10 s, gemessen sind 4,53 s.

### P2 — Stufe 3 von «ist die Antwort gedeckt» auf «ist dieser Satz gedeckt» umbauen

**Evidenz:** Befund 3 und 4 zusammen. Die formale Coverage lässt Scheinbelege durch und
bestraft Sammelbelege; das Gesamturteil von Stufe 3 überfordert kleinere Modelle (ministral:
8 von 16 falsch abgelehnt).

**Vorschlag:** Stufe 2 bleibt, wie sie ist — deterministisch, billig, formal. Stufe 3 bekommt
statt der Frage «ist *die Antwort* vollständig gedeckt» eine Liste von Einzelfragen: «stützt
Abschnitt [n] diesen Satz?». Das ist näher an der NLI-Formulierung der Attributionsliteratur,
deutlich schmaler als ein Gesamturteil, und es ist genau die Zerlegung, die Chain-of-
Verification empfiehlt.

**Warum das auch R05 löst:** Ein Modell, das «vollständig» als Vollständigkeit missversteht,
kann die Frage «stützt [2] diesen Satz» kaum missverstehen. Der geplante R05-Prompt-Fix ist
die kleine Variante davon; dies wäre die grosse.

**Vormessbar:** vollständig offline auf den gespeicherten Antworten und Kontexten.

### P3 — Stufe 0/1 ersetzen oder abschaffen

**Evidenz:** Befund 1 — beide Stufen haben nie gegriffen, und eine trennende Schwelle
existiert nicht.

Zwei ehrliche Optionen, und beide sind besser als der Ist-Zustand:

- **Abschaffen und so dokumentieren.** Die Pipeline ist dann eine dreistufige, und ADR-008
  behauptet nichts mehr, was die Messung nicht deckt.
- **Durch einen inhaltlichen Relevanzentscheid ersetzen** — «decken diese fünf Abschnitte
  das Thema der Frage überhaupt ab?», gestellt vor der Generierung. Das ist der Schritt, den
  Corrective RAG (Yan et al. 2024) als Retrieval-Evaluator einführt, und es ist der einzige
  Mechanismus in Sicht, der die DSGVO/AI-Act-Verwechslung erwischt: dort ist die Ähnlichkeit
  hoch, das Thema aber ein anderes, und keine Formregel im Prompt hat das je gefangen (R02,
  R04).

### P4 — Embedding-Modell messen statt annehmen

`text-embedding-3-small` ist mehrsprachig, aber englischzentriert; der Korpus ist deutsches
Verwaltungs- und Rechtsdeutsch. Mehrsprachige Modelle mit starkem Deutsch-Anteil (BGE-M3,
multilingual-E5, Jina v3) liegen auf deutschen Retrieval-Benchmarks regelmässig vorn. **Das
ist der einzige Vorschlag hier, der die Obergrenze selbst anhebt** — die 0,945 Recall in den
Kandidaten sind auch eine Eigenschaft des Embeddings.

Der Weg ist gebaut: T-42 hat den Dimensionswechsel samt Reindexierung vorgesehen
(`apply_embedding_config.py`). Kosten: eine Reindexierung des Korpus, kein Architekturumbau.

### P5 — Query-Verarbeitung: heute gar keine

Beide Findungsprobleme (`SAMW-JUGENDLICHE-01`, `AIA-ADV-04`) sind Kandidaten für
Query-Rewriting oder HyDE. Der Hebel ist kleiner als P1 bis P4 — zwei Fragen von 56 —, aber
er ist der billigste zu messen, weil er offline gegen den bestehenden Index läuft.

### P6 — Kleinigkeiten mit Belegen

- `ts_rank_cd` ist **nicht** BM25. Postgres' Volltext-Ranking ist schwächer als BM25
  (Robertson & Zaragoza 2009); die sparse Hälfte der Hybridsuche arbeitet damit unter ihren
  Möglichkeiten. Eine BM25-Implementierung in SQL oder eine Erweiterung wäre ein
  abgegrenzter Gewinn.
- Die handgepflegte `STOP_WORDS`-Liste dupliziert, was `to_tsvector('german', …)` ohnehin
  entfernt. Sie ist begründet (die 10-Term-Grenze soll zählen, was gesucht wird), aber sie
  ist eine zweite Wahrheit über dasselbe.
- **Kein `ORDER BY` auf `chunk_index`** beim Kontextaufbau: Die fünf Chunks kommen in
  Fusionsreihenfolge in den Prompt, nicht in Dokumentreihenfolge. Bei mehreren Chunks
  derselben Seite liest das Modell den Text in beliebiger Reihenfolge. Billig zu ändern,
  plausibel wirksam, bisher nicht gemessen.

### Was ich **nicht** empfehle

- **Schwellen je Modell.** Gemessen und verworfen, siehe `Stellschrauben.md`.
- **MMR/Diversifizierung.** Der Kontext ist bereits diversifiziert (Median 5 verschiedene
  Seiten bei 5 Chunks).
- **Die Coverage-Schwelle senken.** Bei der Referenz kämen mit 0,25 sieben Antworten frei,
  zwei davon inhaltlich falsch.

---

## 9. Grenzen dieser Bewertung

- **80 Fragen, ein Lauf je Runde.** Eine Frage entspricht 4,5 Prozentpunkten bei den
  Out-of-Corpus-Zahlen, 2,2 bei den In-Corpus-Zahlen.
- **Zwei Fachkorpora, ein Sprachraum.** Nichts hier ist auf englische oder gemischte Korpora
  übertragbar.
- **Der Holdout (22 Fragen) ist nicht ausgewertet.** Die Recall-Zahlen in Abschnitt 4 sind
  über alle 56 Fragen mit Seitenanker gerechnet, also inklusive Holdout — Retrieval war nie
  Gegenstand einer Optimierungsrunde, eine Überanpassung ist dort nicht möglich.
- **Recall ist seitengenau**, nicht aussagengenau: Steht die erwartete Seite im Kontext, aber
  der tragende Satz auf einer anderen, zählt die Frage als Treffer. Acht Abweichungen der
  Klasse S5 in R04 sind genau solche Fälle — die wahre Obergrenze liegt also **unter** 0,772.
- **Die Literaturangaben sind aus dem Gedächtnis**, ohne Online-Recherche in dieser Sitzung.

---

## 10. Literatur (Kurzliste, zu verifizieren)

| Arbeit | Relevanz hier |
|---|---|
| Cormack, Clarke & Büttcher (2009), *Reciprocal Rank Fusion* | Grundlage der Fusion in `retrieval.py`; `k=60` stammt von dort |
| Robertson & Zaragoza (2009), *The Probabilistic Relevance Framework (BM25)* | Massstab für die sparse Hälfte; `ts_rank_cd` bleibt darunter |
| Karpukhin et al. (2020), *Dense Passage Retrieval* | Warum dense und sparse sich ergänzen |
| Lewis et al. (2020), *Retrieval-Augmented Generation* | Die Grundarchitektur |
| Nogueira & Cho (2019), *Passage Re-ranking with BERT*; Nogueira et al. (2020), *monoT5* | Beleg für P1 — Re-Ranking als stärkster Einzelhebel nach dem Retrieval |
| Gao et al. (2022), *HyDE* | Beleg für P5 — Query-Transformation |
| Gao et al. (2023), *Enabling LLMs to Generate Text with Citations* (ALCE) | Citation Precision/Recall per NLI — Beleg für P2 |
| Liu et al. (2023), *Lost in the Middle* | Positionseffekte; relevant, sobald `context_top_n` steigt |
| Dhuliawala et al. (2023), *Chain-of-Verification* | Zerlegung des Gesamturteils — Beleg für P2 |
| Asai et al. (2023), *Self-RAG*; Yan et al. (2024), *Corrective RAG* | Gelernter statt schwellenbasierter Relevanzentscheid — Beleg für P3 |
| Es et al. (2023), *RAGAS* | Evaluationsrahmen; ADR-009 nennt es |
| Chen et al. (2024), *BGE-M3* | Kandidat für P4 |
| Sarthi et al. (2024), *RAPTOR* | Hierarchische Zusammenfassung — Option, wenn der Korpus wächst |

---

## 11. Vorschlag für die Reihenfolge

R05 ist bereits gesetzt (Self-Check-Prompt). Danach in dieser Reihenfolge, jeweils zuerst
offline auf den gespeicherten Läufen:

1. **R06 — `context_top_n` 5 → 10.** Keine neue Komponente, misst den Recall-Gewinn gegen
   den Coverage-Verlust. Beantwortet nebenbei, wie viel ein Re-Ranker überhaupt holen kann.
2. **R07 — LLM-Re-Ranking**, offline auf den Kandidatenlisten vorgemessen.
3. **R08 — Stufe 3 satzweise** statt als Gesamturteil (P2).
4. **Danach:** Embedding-Wechsel (P4) als eigener Schnitt, weil er eine Reindexierung braucht
   und alle vorherigen Messungen ungültig macht.

Befund 1 (Stufe 0/1 wirkungslos) braucht keine Runde, sondern einen Entscheid — er gehört als
Nachtrag in ADR-008, unabhängig davon, ob die Stufen ersetzt oder gestrichen werden.
