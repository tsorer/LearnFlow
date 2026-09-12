# Befunde zur In-Corpus-Messreihe vom 2026-09-11 (T-56)

Lauf von `eval/test_in_corpus_quality.py` gegen den indexierten Korpus
(200 + 210 + 525 Chunks), Profil `openai` (`gpt-4o-mini`), Seed-Defaults
(`eval/conftest.py::SEED_DEFAULTS`), Git-SHA `41022b7`. Alle Zahlen unten
stehen unverändert im `run.json` dieses Laufs (lokal, gitignored) — seit dem
Review auf #131 trägt es auch die Gruppe-B-Aggregate, vorher nur per
Ad-hoc-Skript über `results.csv` rekonstruierbar.

## 1. Halluzinationsrate hält das Gate — 0 % über 33 ausgelieferte Antworten

`hallucination_rate = 0.0` (`hallucination_pool_size = 33`: die 45
`in_corpus`- und 11 `adversarial`-Fragen mit `expected_refusal: false`,
abzüglich der tatsächlich unterdrückten — 28 in_corpus- und 5
adversarial-Antworten wurden ausgeliefert). Keine davon hat H1 (erfundene
Referenz) oder H2 (Antwort stützt sich auf ein anderes Dokument als das
zugesagte) ausgelöst — auch nicht `AIA-ADV-01`/`AIA-ADV-04` (Fragen zum
Geltungsbereich, die frühere Läufe laut `2026-09-10_Befunde.md` Punkt 4
anfällig für genau diese Verwechslung zeigten) oder `AIA-ADV-02`/`-03`/`-05`
(falsche Absolutaussagen, die eine Korrektur statt eine Bestätigung
verlangen).

**Einordnung:** Das ist eine Demonstration auf 33 Fällen, keine Garantie
(ADR-009, "statistische Ehrlichkeit") — und misst nur die mechanisch
erkennbare Fehlerklasse aus H1/H2 (falsches Dokument, erfundene Referenz),
nicht Faithfulness im umfassenden Sinn (dafür bräuchte es einen Judge, bewusst
nicht Teil von T-56, siehe ADR-009 Punkt 7). Innerhalb dieser Grenzen: kein
Handlungsbedarf.

## 2. False-Suppression-Rate reisst den 15-%-Startwert deutlich — 37,8 % (17/45)

Das ist der erwartete Befund, nicht ein Fehler in der Messung: ADR-009 nennt
15 % ausdrücklich als **Startwert**, zu kalibrieren im Spike-Loop (T-57,
#125). Das Gate ist hart geblieben (`assert false_suppression_rate <= 0.15`
reisst den Lauf), wie im Issue verlangt — nicht das Gate wurde aufgeweicht,
sondern der Befund liegt jetzt vor.

| Unterdrückungsgrund | Anzahl |
|---|---|
| `citation_coverage` (Antwort erzeugt, aber Coverage < 0,5) | 9 |
| `generation_refused` (Modell antwortet WEISS_NICHT) | 8 |

Ein Beispiel für `generation_refused`, weil es zeigt, dass die Ursache nicht
im Retrieval liegt: `SKOS-PRINZ-02` ("Was bedeutet das
Bedarfsdeckungsprinzip?") — ein SKOS-Grundbegriff, eindeutig im Korpus
enthalten. Beide deterministischen Gates passieren mit Reserve
(`retrieval_gate`: 0,5549 ≥ 0,35; `retrieval_confidence`: 0,5216 ≥ 0,40), fünf
Chunks gehen in den Kontext — darunter allerdings einer aus dem **EU-AI-Act**-
Korpus statt aus den SKOS-Richtlinien (Kontamination über die
Fusionsrangliste, kein Filter nach Korpus in der Retrieval-Query). Das Modell
selbst antwortet `WEISS_NICHT` (`debug.llm_calls[0].response`). Die Ursache
liegt damit vor Stufe 2, im Zusammenspiel aus Kontextauswahl und
Generierungs-Prompt — nicht in einer zu strengen Schwelle. Das ist eine
qualitativ andere Klasse als die neun `citation_coverage`-Fälle (Antwort
wurde erzeugt, aber zu wenig davon trug eine gültige Fussnote) und dürfte für
T-57 relevant sein: `min_citation_coverage` senken behebt die
`generation_refused`-Fälle nicht.

## 3. Adversarial-Refusal: 1 von 2 (kein Gate, n zu klein)

`SKOS-ADV-02` (suggestiv vorgegebene Zahl CHF 997) wird korrekt verweigert.
`SKOS-IPV-02` wird ausgeliefert, obwohl das Dataset Verweigerung erwartet —
die Antwort selbst ist aber nicht falsch: sie bleibt bei der qualitativen
Aussage, die die Dataset-Notiz als beleg­bar nennt ("Höhe und
Anspruchsvoraussetzungen kantonal unterschiedlich", C.5 Erl. a/b), und lehnt
den quantitativen Teil der Frage explizit ab ("Der Kontext deckt jedoch nicht
ab, ob..."). Fachlich ist das näher an der Nuance-Antwort, die auch
`SKOS-ADV-01` erwartet, als an einer erfundenen Zahl. Mit n=2 trägt das kein
Gate; für eine belastbare Aussage bräuchte diese Kategorie mehr Fragen.

## 4. Context-Recall/Precision/MRR — top-k vs. Kontext

| Schnitt | Fragen (bewertet) | Recall | Precision | MRR |
|---|---|---|---|---|
| top-k, in_corpus | 45 | 95,4 % | 5,3 % | 0,727 |
| top-k, adversarial | 11 | 90,9 % | 5,1 % | 0,542 |
| Kontext (`in_top_n`), in_corpus | 45 | 78,3 % | 22,7 % | 0,719 |
| Kontext (`in_top_n`), adversarial | 11 | 72,7 % | 14,5 % | 0,515 |

"Fragen (bewertet)" bei adversarial ist 11, nicht 13: die beiden
`expected_refusal: true`-Fragen (`SKOS-ADV-02`, `SKOS-IPV-02`) tragen keine
`expected_source` und gehen nicht in die Mittelung ein — `run.json` führt das
seit dem Review auf #131 explizit als `scored_questions` mit, statt die
Fragenzahl der Kategorie fest zu beschriften (der Vorläufer dieser Datei tat
das und war damit für adversarial falsch beschriftet).

Erwartbares Muster, keine Überraschung: top-k (`retrieval_top_k=20`) hat hohen
Recall bei niedriger Precision (viel wird geholt, wenig davon ist die
erwartete Seite), der Kontext-Schnitt (`context_top_n=5`) verdichtet auf mehr
Precision bei einem gewissen Recall-Verlust — plausibel, dass genau dieser
Verlust an der False-Suppression von Punkt 2 mitwirkt: eine relevante Seite,
die es in die Top-20 schafft, aber nicht in die Top-5 des Kontexts, kann
weder zitiert noch belegt werden. Eine Aussage über die *richtige* Grösse von
`context_top_n` ist das nicht — dafür ist T-57 da.

## 5. Lauf-zu-Lauf-Schwankung

Mehrere Läufe desselben Tages, unverändertem Korpus: False-Suppression
zwischen 33,3 % und 37,8 % (15–17 von 45). Dieselbe Beobachtung wie in
`2026-09-10_Befunde.md` Punkt 2b für den Refusal-Test: OpenAI sichert
Reproduzierbarkeit auch bei `TEMPERATURE = 0.0` nicht zu. Für die Einordnung
oben ändert das nichts — alle Läufe liegen deutlich über 15 % —, ist aber
relevant für T-57: ein einzelner Kalibrierungslauf ist kein verlässlicher
Vergleichspunkt für eine Parameteränderung im einstelligen Prozentbereich.

## Was daraus folgt

1. **Kein Handlungsbedarf am Halluzinations-Gate.** 0 % über 33 ausgelieferte
   Antworten, Reserve unbekannt (Demonstration, keine Garantie).
2. **Handlungsbedarf am False-Suppression-Gate — das ist der eigentliche
   Zweck dieses Issues.** 37,8 % gegen 15 % Startwert, mit einer Ursache
   (`generation_refused` trotz sauberem Retrieval, siehe `SKOS-PRINZ-02`), die
   eine reine Schwellenverschiebung nicht behebt. Geht an **T-57 (#125)**.
3. **Der Kontext-Recall-Verlust gegenüber top-k (95 % → 78 %) ist ein
   plausibler Kandidat für einen Teil von Punkt 2** — zu prüfen in T-57, nicht
   hier entschieden.
4. Die Recall/Precision/MRR-Zahlen sind Eingabe für die Kalibrierung, kein
   Befund für sich (ADR-009 nennt für Gruppe B keinen Schwellenwert).
