# Stellschrauben-Katalog

Was eine Stellschraube bewirkt, belegt mit der Runde, in der es gemessen wurde. Eine Zeile
entsteht erst mit Evidenz — Vermutungen stehen in den Runden-Dokumenten als Hypothese.

| Stellschraube | Ort | Wirkung (beobachtet) | modellabhängig? | Evidenz |
|---|---|---|---|---|
| `num_ctx` | Profil (Ollama) | Ohne Angabe 4096 Tokens; Ollama kürzt den Prompt von vorn, die Systemanweisung geht verloren → leere Antworten, als Verweigerung gezählt | ja (Ollama) | `2026-09-10_Befunde.md`, 1 |
| `max_verdict_tokens` | Profil | Zu klein für Modelle mit Denk-Vorlauf → leeres Urteil, fail-closed unterdrückt | ja | `2026-09-10_Befunde.md`, 1; R00 (gemma4, 1000 → 4000) |
| `think` | Profil | qwen3: `false` spart ~50 s je Aufruf bei gleicher Antwort; gpt-oss: nur Stufen, kein Abschalten | ja | `profiles.py`; R00 |
| `MIN_SEGMENT_WORDS` = 4 | `confidence.py` | Belegte Listenpunkte unter 4 Wörtern zählen nicht; Antworten wie «NEIN [1].» erreichen Coverage 0,0 | nein — trifft Modelle, die knapp aufzählen | R00, 5.2 |
| Satzzerlegung (`_SENTENCE_BOUNDARY`, Abkürzungen) | `confidence.py` | Ordinalzahlen («14.») und «(z. B.» trennen Sätze, Belege gehen verloren | nein | R00, 5.2 |
| Referenzformat (`_REFERENCE`) | `confidence.py` | Erkennt `[1]`, `[1, 2]`; nicht `【1】`, `[1a]`, `[1.2]`, `[1(3a)]` → korrekt belegte Antworten gelten als unbelegt | ja — Format ist modelltypisch | R00, 5.3 |
| Prompt Regel 2 (Beleg je Aussage) | `generation.py` | Wird von gpt-4o-mini und gpt-oss als Sammelbeleg umgesetzt | ja | R00, 5.3 |
| Prompt Regel 3 vs. 4 (Verweigern vs. Teilantwort) | `generation.py` | Teilantworten mit benannter Lücke zählen bei Out-of-Corpus-Fragen als Fehler; Stufe 2 bestraft den Lückensatz | ja | R00, 5.2 und 7 (gemma4) |
| Fehlende Regel für falsche Prämissen | `generation.py` | Modelle verweigern, statt die Annahme mit Beleg zu korrigieren | modellübergreifend | R00, 5.4 |
| `_is_refusal` (`startswith`) | `generation.py` | Sentinel mitten im Text wird nicht als Verweigerung erkannt | ja (P3 bei qwen3, ministral) | R00, 5.6 |
| Satzzerlegung, 4 Regeln (Ordinalzahl, Klammer-Abkürzung, Einleitung, belegter Listenpunkt) | `confidence.py` | False-Suppression Dev: gemma4 4 → 2, ministral 13 → 10, gpt-oss −2 (rauschfrei); openai, qwen3 unverändert; keine unbelegte Aussage neu als belegt | ja — wirkt bei Modellen mit Aufzählungen und Datumsangaben | R01 |
| Coverage ↔ Self-Check-Band | `confidence.py`, `config` (Bänder) | Genauere Coverage hebt die Konfidenz über 0,75; Self-Check läuft seltener (live, Dev, alle Modelle 70 → 53) | nein — Folge der Bandgrenzen | R01 |
| Reproduzierbarkeit bei Temperatur 0 | Modell / Ollama | Gleiche Eingabe einen Tag später: gpt-oss 48/80 wortgleich, gemma4 80/80 | ja | R01 |
| Prompt Regel 2 präzisiert (Beleg je Satz/Listenpunkt, nur Nummer) | `generation.py` | Unbelegte Aussagen: gpt-4o-mini 41 → 28 %, gpt-oss 56 → 41 %, ministral 36 → 21 %; False-Suppression Dev gpt-oss 14 → 8, Referenz 10 → 8; bei qwen3 Out-of-Corpus-Refusal 68 → 59 % | ja | R02 |
| Tolerantes Lesen fremder Referenzformate (`[1a]`, `【1】` → `[1]`) | `confidence.py` (nur offline) | Ohne Prompt-Änderung ministral −4; nach R02a nur −1, und diese Antwort ist inhaltlich falsch — verworfen | ja | R02 |
| Formtreue ↔ Inhaltsfilter | Stufe 2 | Wer jeden Satz belegt, belegt auch falsche: Verwechslung mit Coverage 1,0 ausgeliefert. Stufe 2 filterte bisher nebenbei Inhalte | modellübergreifend | R02, 5.1 |
| «Nummer des Abschnitts» mehrdeutig | `generation.py` | Modelle zitieren nummerierte Absätze aus dem Dokument (`[13]`, `[65]`) → `citation_invalid` | ja (ministral, gpt-oss) | R01, R02 |
| Prompt-Ausnahme für falsche Annahmen (in Regel 3 angehängt) | `generation.py` | Ohne Wirkung: Annahme-Fragen je Modell ±1 (openai 4→4, qwen3 5→5, gpt-oss 3→4, ministral 2→3); zurückgenommen. Die Ausnahme stand hinter «antworte ausschliesslich mit WEISS_NICHT» | modellübergreifend | R03 |
| Endlosschleife als Artefaktform | Modell / Budget | qwen3 wiederholte 13 min denselben Satz bis 8000 Tokens; als abgeschnitten unterdrückt, zählt fälschlich als «richtig verweigert» | ja | R03, 5.2 |
| Regeln 3 und 4 als **eine** Entscheidung mit drei Fällen | `generation.py` | Out-of-Corpus-Refusal qwen3 59 → 68 %, gemma4 82 → 86 %, gpt-oss 91 → 96 %, Referenz unverändert 91 %; False-Suppression sinkt bei zwei Profilen, steigt bei ministral 31 → 40 % | ja — Richtung stimmt bei vier von fünf | R04, 4.1 |
| **Länge** des Regelblocks | `generation.py` | Längere Regeln → längere Antworten bei **gleich vielen** Belegen. Zeichen je Beleg: Referenz 178 → 194, gpt-oss 200 → 251, ministral 129 → 142. Da Stufe 2b die Belegdichte misst, sinkt die Coverage mit | ja | R04, 4.2 |
| Denk-Vorlauf reagiert auf die Promptlänge | Modell / Budget | gemma4: derselbe Prompt mit längerem Regelblock verdoppelt den unsichtbaren Anteil (Median 858 → 1535 Completion-Tokens, 2,43 → 4,11 Tokens je sichtbarem Zeichen); zwei Fragen laufen ins 8000er-Limit und kommen **leer** zurück. Andere Profile: +10 bis +20 % | ja — nur bei unbeschränktem Denkmodus | R04, 4.7 |
| «**vollständig** gedeckt» im Self-Check-Prompt | `self_check.py` | Einleitungssatz und Regel 1 benutzen dasselbe Wort gegensätzlich. ministral liest daraufhin *Vollständigkeit* statt *Deckung*: 8 von 16 Urteilen `NICHT_GEDECKT`, gegen genau eines bei allen anderen Profilen zusammen | ja — gpt-4o-mini löst die Mehrdeutigkeit richtig auf | R04, 4.3 |
| Scheinbelege bei Prosa-Verweigerung | Stufe 2b | «… enthält keine Angabe. [1][2][3][4][5]» erreicht Coverage **1,0** und wird ausgeliefert. Stufe 2b zählt, *ob* eine Nummer hinter einer Aussage steht, nicht *ob* sie stützt | ja (qwen3) | R04, 4.4 |
| `min_citation_coverage` **je Modell** | `config` | Gemessen und **verworfen** — siehe Abschnitt unten. Die Coverage-Verteilung ist zweigipflig; eine gesenkte Schwelle befreit wenige Antworten und schleppt falsche mit | scheinbar ja, tatsächlich nein | R04, `werkzeuge/schwellen.py` |

---

## Braucht jedes Modell seinen eigenen Parametersatz?

Die Frage liegt nahe, wenn dieselbe Prompt-Änderung bei drei Modellen hilft und bei einem
schadet (R04). Die Antwort ist je Schicht der Pipeline eine andere — und bei der Schicht, wo
man sie zuerst vermutet, lautet sie **nein**.

### 1. Retrieval-Parameter — modellunabhängig per Konstruktion

`retrieval_top_k`, `rrf_k`, `context_top_n`, `similarity_threshold` und
`min_retrieval_confidence` entscheiden, **bevor** das Sprachmodell gefragt wird. Kein
Messwert dieser Reihe kann von ihnen modellabhängig sein, weil das Modell zu diesem
Zeitpunkt noch gar nicht beteiligt ist. Einmal kalibrieren genügt für alle Modelle — das ist
der übertragbare Teil des Kalibrierungs-Loops aus T-57 (Schicht A1/A2).

### 2. `min_citation_coverage` — sieht modellabhängig aus, ist es aber nicht nützlich

Nachgerechnet auf R04 (Entwicklungs-Set, `werkzeuge/schwellen.py`). Die Coverage-Werte der
Antworten, die Stufe 2b unterdrückt hat, je Profil — `r` = inhaltlich richtig, `f` = falsch,
nach `labels/R04.csv`:

```
openai            |  7 | 0,33r 0,33r 0,33r 0,33f 0,33? 0,25r 0,25f
qwen3-local       |  0 |
gpt-oss-local     | 10 | 0,33r 0,33r 0,33r 0,25r 0,00r 0,00r 0,00r 0,00r 0,00r 0,00?
ministral3-local  |  3 | 0,44r 0,29f 0,00r
gemma4-local      |  0 |
```

Und was eine gesenkte Schwelle einbrächte (`f` = davon inhaltlich falsch):

| Profil | heute 0,5 | bei 0,4 | bei 0,3 | bei 0,25 |
|---|---|---|---|---|
| `openai` | 7 unterdrückt | 0 (0f) | 5 (**1f**) | 7 (**2f**) |
| `gpt-oss-local` | 10 unterdrückt | 0 (0f) | 3 (0f) | 4 (0f) |
| `ministral3-local` | 3 unterdrückt | 1 (0f) | 1 (0f) | 2 (**1f**) |
| `qwen3-local`, `gemma4-local` | 0 unterdrückt | — | — | — |

Drei Beobachtungen, und jede spricht gegen eine Schwelle je Modell:

1. **Bei zwei von fünf Profilen ist die Schwelle wirkungslos** — qwen3 und gemma4 haben keine
   einzige Coverage-Unterdrückung. Ein «optimaler Wert» ist für sie nicht bestimmbar.
2. **Bei gpt-oss liegen 6 der 10 Fälle bei Coverage 0,00** — das Modell hat überhaupt keinen
   gültigen Beleg gesetzt. Dagegen hilft keine Schwelle über null; erreichbar sind 3 bis 4
   Fälle.
3. **Wo Senken hilft, schleppt es Falsches mit.** Bei der Referenz kämen mit 0,25 sieben
   Antworten frei, zwei davon inhaltlich falsch — genau die Richtung, die ADR-008 verbietet.

Die Verteilung ist **zweigipflig**: Antworten sind entweder sauber belegt (≥ 0,5, kommen
durch) oder katastrophal unbelegt (0,00–0,33). Dazwischen liegt fast nichts. Der wirksame
Hebel ist deshalb der Prompt und nicht die Schwelle — R02a hat bei gpt-oss die unbelegten
Aussagen von 56 % auf 41 % gedrückt, ohne einen Schwellenwert anzufassen.

### 3. Self-Check-Band und Stufe 3 — hier ist die Modellabhängigkeit real

| Profil | Stufe 3 gelaufen (von 58) | GEDECKT | NICHT_GEDECKT |
|---|---|---|---|
| `openai` | 16 | 15 | 1 |
| `qwen3-local` | 4 | 4 | 0 |
| `gpt-oss-local` | 12 | 12 | 0 |
| `ministral3-local` | **16** | 8 | **8** |
| `gemma4-local` | 5 | 5 | 0 |

Bandbelegung 4 bis 16, Ablehnungsquote 0 % bis 50 % — das ist die grösste Streuung aller
gemessenen Grössen. Trotzdem ist die erste Antwort auch hier nicht «ein Band je Modell»:
ministrals Ablehnungen sind Fehlurteile (R04, 4.3), und ein enger gestelltes Band würde sie
umgehen statt beheben. Ein Parameter, der ein kaputtes Urteil unsichtbar macht, verbessert
die Kennzahl und nicht das System.

### 4. Was schon heute legitim je Modell ist

Ein modellspezifischer Parametersatz **existiert bereits** — an der richtigen Grenze.
`eval/profiles.py` erlaubt Modell und **Budgets**: gemma4 braucht `max_answer_tokens: 12000`,
wo die Referenz mit 800 auskommt, `max_verdict_tokens: 4000` gegen 1000, `num_ctx: 16384`
überall, `think: false` bei qwen3 und `think: "low"` bei gpt-oss. Das sind keine
Qualitätsparameter, sondern die Frage, ob das Modell überhaupt Platz und Zeit zum Antworten
hat.

Die Grenze ist ausdrücklich gezogen und getestet: `tests/test_eval_profiles.py` schlägt fehl,
sobald `Profile` ein Feld `similarity_threshold`, `min_citation_coverage` oder eine Bandgrenze
bekommt — «die Schwellen sind Gegenstand der Messung, nicht ihr Rahmen». Ein goldener
Parametersatz je Modell würde genau diese Regel kippen.

### Was er kosten würde

Er kollidiert mit der Maintainability-NFA («LLM-Provider wechselbar durch Konfiguration —
kein Code-Change»). Der *Provider* bliebe wechselbar, die *Zuverlässigkeitszusage* nicht: ein
Modellwechsel wäre kein Config-Change mehr, sondern ein Kalibrierungsprojekt mit eigenem
Holdout und echten Token-Kosten. Das CI-Gate aus ADR-009 müsste eine Matrix führen statt
einer Zeile.

### Vorgehen, um ein lokales Modell zu bewerten

1. **Ein Live-Lauf** mit dem Produktivparametersatz, 80 Fragen. Mehr nicht — ein Lauf je
   Runde ist die bewusste Festlegung aus `00_Vorgehen.md`.
2. **Abweichungen einordnen**, getrennt nach Urteilsfähigkeit und Protokolltreue. Das ist die
   eigentliche Entscheidung: gpt-oss liegt bei 0,948 / 0,810 — es urteilt besser als die
   Referenz und zitiert schlechter. Das ist ein Kandidat. Umgekehrt wäre es keiner.
3. **Alles Weitere offline.** Coverage und Bänder sind reine Arithmetik über die
   gespeicherten Antworten; ein Live-Lauf trägt beliebig viele Schwellenfragen. So wurde R01
   zweimal bewiesen, so wird R05 gemessen.
4. **Modellspezifische Schwellen erst, wenn die Protokollarbeit ausgereizt ist** — und dann
   als Teil des Modell-Steckbriefs, mit eigenem Holdout und der ausdrücklichen Feststellung,
   was man damit aufgibt.
