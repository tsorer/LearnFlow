# Block 5 — Themenübersicht (top down)

Arbeitspapier für den Neuaufbau, gleiche Methode wie [`Block2_Themen.md`](Block2_Themen.md):
erst entscheiden, **was** in den Block gehört, dann bauen. Der Stand vom 19.09.
(`Archive/Block5_Fazit-Ausblick.html`, 6 Folien, ~3:35) war stark auf die Wortsuche
konzentriert — die ist jetzt in Block 2 erzählt und wird hier frei.

**Seit dem 19.09. hat sich die Faktenlage geändert:** T-57 (Kalibrierungs-Loop) und T-63
(Architektur-Hygiene) sind auf `main`. Die alte Folie 1 nennt beide als «bewusst offen» —
das stimmt nicht mehr, und die Korrektur macht den Block *besser*: Wir haben nicht nur
vorgehabt zu kalibrieren, wir haben es getan, und das Ergebnis ist der interessanteste Befund
des Projekts.

---

## 1 · Wozu dient Block 5?

Er kommt nach Christophs Learnings und ist das Letzte, was das Publikum hört. Drei Fragen,
mehr nicht:

> **Hält das Produktversprechen? — Wo ist der grösste Hebel? — Was ist als Nächstes dran?**

Vorgaben aus Retos Gliederung: keine Deadlines, keine Stundenzahlen, keine Detailroadmap.
Offenes als bewusste Priorisierung framen, nicht als Rückstand. Lokale Modelle sind
ausdrücklich gewünscht.

Prüfstein für jedes Thema: **Würde ein Zuhörer es weitererzählen?** Ein Ausblick, der nur
Issue-Nummern aufzählt, wird nicht weitererzählt. Ein Team, das sein eigenes bestes Ergebnis
auseinandernimmt, schon.

---

## 2 · Themenkatalog

### T1 · Das Versprechen hält — und die Kennzahl, die das zu gut aussehen lässt

- **Was:** 0 % Halluzination, in jeder Runde, bei jedem der fünf Modelle. Das ist das
  Produktversprechen aus Christophs Einstieg, gemessen.
- **Der interessante Teil:** Diese 0 % entstehen teils aus dem Zuschnitt des Nenners. Der
  Halluzinations-Pool zählt nur `in_corpus`- und bewertete `adversarial`-Fragen; **ausgelieferte
  Antworten auf Fragen ausserhalb des Korpus fliessen nicht ein**. Rechnet man streng über alle
  ausgelieferten Antworten, liegt die Referenz bei **2,9 %** (1 von 34) — und jede einzelne
  falsche Antwort steht in genau der Kategorie, die der offizielle Nenner ausschliesst. Das
  schärfste Gate misst an der gefährlichsten Kategorie vorbei.
- **Was daraus folgt:** nicht «die Pipeline halluziniert doch», sondern «die Kennzahl gehört
  repariert». 2,9 % sind für RAG ein guter Wert — nur eben nicht null.
- **Beleg:** `kennzahlen.csv` (Spalte `halluzination_alle`, alle Runden 0,0) ·
  `Pipeline-Review.md` §2a.1 (beides auf dem T-62-Branch).
- **Achtung:** Die Literaturvergleiche in §2a.1 (RAGTruth, FACTS Grounding) sind dort
  ausdrücklich «aus dem Gedächtnis, zu verifizieren». **Nicht auf die Folie**, solange sie
  niemand nachgeprüft hat. Die Aussage trägt auch ohne sie.
- **Zeit:** 0:45 · **Urteil: Kern.** Das ist die ehrlichste Folie, die wir haben, und sie kommt
  von uns selbst — nicht von einem Reviewer.

### T2 · Wir haben aufgehört zu raten — und gemerkt, dass die Messgrundlage zu klein ist

- **Was:** Bis vor kurzem waren die Schwellenwerte Startwerte aus ADR-009 plus Handjustage
  (beim Eval-Lauf am 09.09. stand `min_citation_coverage` auf 0,28 statt 0,50). T-57 ersetzt
  das: Der Suchteil wird offline auf einem eingefrorenen Schnappschuss durchgerechnet, nur die
  besten Kandidaten laufen echt gegen das Modell.
- **Das Ergebnis ist der Befund:** Das empfohlene Parameter-Set erfüllt auf dem Trainingsteil
  beide Gates — und fällt auf dem Holdout durch: Ablehnungsrate 85,7 % gegen das 90-%-Gate,
  fälschlich unterdrückt 33,3 %. Der Grund ist nicht das Set, sondern die Auflösung: Bei
  **7 Holdout-Fragen ausserhalb des Korpus bewegt eine einzige Frage die Rate um 14,3
  Prozentpunkte**.
- **Und noch schärfer:** Derselbe Code, dasselbe Parameter-Set, zwei aufeinanderfolgende Tage →
  26,7 % und 33,3 %. Allein Lauf-zu-Lauf-Streuung.
- **Konsequenz, und das ist die Pointe:** Die alten Startwerte bleiben in Kraft, weil ADR-008
  fail-closed ist. Der nächste Hebel ist nicht ein besserer Suchalgorithmus, sondern **ein
  grösseres Gold-Dataset**. Man kann nicht feiner steuern, als man messen kann.
- **Beleg:** `Docs/10_Kalibrierungsbericht.md` (Lauf vom 16.09.) · GitHub #125/#139.
- **Zeit:** 0:50 · **Urteil: Kern.** Das stärkste Learning des Projekts, und es ist neu
  gegenüber dem 19.09.-Stand.

### T3 · Temperatur 0 heisst nicht reproduzierbar

- **Was:** Bei identischem Code und `TEMPERATURE = 0` lieferte `gpt-4o-mini` zwischen zwei Tagen
  **15 von 80** Antworten anders.
- **Warum es zählt:** Jeder Vergleich «vorher/nachher» aus einem einzelnen Lauf ist damit
  angreifbar — auch unsere eigenen Optimierungsrunden. Das ist die Erklärung für die Streuung
  in T2 und der Grund, warum wir Einzelläufe nicht als Beweis verkaufen.
- **Beleg:** `R00_Baseline.md`, `Docs/10_Kalibrierungsbericht.md` (Methodische Hinweise).
- **Zeit:** 0:20 · **Urteil: Teil von T2**, keine eigene Folie — dort ist es die Begründung,
  allein stehend ist es eine Fussnote.

### T4 · Der grösste Hebel: ein Rangproblem, kein Fundproblem

- **Was:** Von 15 fehlenden Quellen lagen **13 in der Kandidatenliste** — gefunden, aber beim
  Schnitt auf fünf verloren. Ein Re-Ranker zwischen Mischen und Gate bewertet die Kandidaten
  nach Inhalt, bevor geschnitten wird. Kopfraum: **+17 Prozentpunkte**, der grösste einzelne
  Hebel in der ganzen Analyse.
- **Anschluss an Block 2:** Genau das war dort an Q1 zu sehen — die beste Antwort auf dem
  letzten Kontextplatz. Und die Wortsuche-Bilanz (hilft 3×, schadet 5×) ist dasselbe Thema:
  blindes Mischen nutzt nur die Hälfte des Werts der zweiten Suche.
- **Die Architekturfrage dahinter, die es ehrlich macht:** ADR-005 hält PyTorch aus dem Backend
  heraus, ein klassischer Cross-Encoder fällt damit aus. Bleiben ein zusätzlicher Modellaufruf
  über LiteLLM oder ein gehosteter Re-Ranker — ein weiterer Anbieter und damit eine
  Datenschutzfrage vor dem Pilot. Latenzbudget: p95 ≤ 10 s (Quality Attributes), die Referenz
  liegt heute im Median bei gut einer Sekunde pro Antwort.
- **Beleg:** `Pipeline-Review.md` §4 und §8 P1 · `Pipeline-Trace/wortsuche_bilanz.py`.
- **Zeit:** 0:45 · **Urteil: Kern.** Das ist die Antwort auf «wo ist Potenzial».

### T5 · Zwei Stufen, die noch nie etwas blockiert haben

- **Was:** Stufe 0 und Stufe 1 haben über alle Läufe **keine einzige Frage** blockiert. Beide
  Schwellen liegen unter dem, was in der Praxis vorkommt.
- **Warum es interessant ist:** Im Code sehen sie wie Sicherheit aus. Gemessen sind sie
  wirkungslos — die inhaltliche Last trägt Stufe 3, und Stufe 2 misst Form, nicht Stützung. Eine
  Schwelle, die nie greift, gehört ersetzt oder abgeschafft und ehrlich dokumentiert; sie darf
  nicht als Schutz gelten, den es nicht gibt.
- **Beleg:** `Pipeline-Review.md` Befunde 1, 3 und 4.
- **Zeit:** 0:25 · **Urteil: zusammen mit T4 auf eine Folie** («was wir ändern würden»), sonst
  wird der Block zur Befundliste.

### T6 · Lokale Modelle — machbar, noch nicht gut genug

- **Was:** Fünf Modelle durch dieselbe Pipeline. Ein Modellwechsel ist kein Komponententausch:
  Das Modell muss das Ausgabeprotokoll bedienen — `WEISS_NICHT`, Belege `[n]`,
  `GEDECKT`/`NICHT_GEDECKT`.
- **Die interessante Zahl ist nicht die schlechteste, sondern der Zielkonflikt:**

  | Modell | lehnt fremde Fragen ab | unterdrückt richtige Antworten | Zeit je Antwort (Median) |
  |---|---|---|---|
  | gpt-4o-mini (Referenz) | 90,9 % | 22,2 % | 1,2 s |
  | ministral-3:14b | 95,5 % | 40,0 % | 16,0 s |
  | gpt-oss:20b | 95,5 % | 37,8 % | 10,4 s |
  | qwen3:8b | 68,2 % | **6,7 %** | 5,9 s |
  | gemma4:26b | 86,4 % | 11,1 % | 58,3 s |

  Die beiden Modelle, die fremde Fragen am besten ablehnen, unterdrücken auch am meisten
  richtige. Das vorsichtigste Modell ist nicht das beste — **zu vorsichtig ist auch ein
  Fehler**. Und die Hardware ist der Filter: Kein lokales Modell passt mit 16K-Kontext
  vollständig in 8 GB VRAM.
- **Beleg:** `kennzahlen.csv` Runde R04 · `EvalAnalysis/Optimierung/Modelle.md`.
- **Zeit:** 0:40 · **Urteil: Kern** — steht so in Retos Gliederung.

### T7 · Was als Nächstes dran ist

- **Reihenfolge mit Begründung, nicht Backlog-Liste.** Erst der Massstab, dann der Hebel, dann
  der Betrieb:
  1. **Der Massstab** — Gold-Defekte bereinigen (T-65, #142), die Halluzinations-Kennzahl um die
     ausgelieferten Out-of-Corpus-Antworten erweitern, das Dataset vergrössern. Ohne das ist
     jede weitere Messung Rauschen.
  2. **Das Gate scharf stellen** — Eval im CI (T-53, #110). Heute läuft es von Hand.
  3. **Der Hebel** — Re-Ranker messen (P1), danach die kleineren Stellschrauben: die Frage mit
     demselben Parser zerlegen wie das Dokument, Hilfsverben als Füllwörter, besseres
     Volltext-Ranking. Alle **nicht gemessen** — genau deshalb stehen sie hier und nicht im Code.
  4. **Betrieb und Hygiene** — Konfiguration an einer Stelle (T-64, #138), Frontend (T-58, #127),
     Kleinkram (T-59/60/61).
- **Erledigt, nicht mehr als offen nennen:** T-57 (Kalibrierungs-Loop) und T-63
  (Architektur-Hygiene) sind auf `main`. T-62 liegt auf einem Branch.
- **Je ein Satz, nicht mehr:** Vor dem Pilot der Wechsel auf Azure OpenAI EU (ADR-004,
  Vorbedingung für echte interne Dokumente). Post-MVP: SSO, Erkennung veralteter Inhalte.
- **Zeit:** 0:35 · **Urteil: Kern**, aber streng auf vier Punkte begrenzen.

### T8 · Schluss

- «Keine Antwort ohne Beleg» hält. Und das, was wir dazugelernt haben: **Der Beleg dafür, dass
  es hält, ist die eigentliche Arbeit.»**
- **Zeit:** 0:20 · **Urteil: Kern.**

### T9 · Was nicht mehr in Block 5 gehört

| Thema | Warum nicht |
|---|---|
| Die Wortsuche ausführlich (3 Folien im alten Deck) | steht jetzt in Block 2, Folien 8–11. Hier nur noch als Begründung für den Re-Ranker, ein Satz |
| Die vier Optimierungsrunden R01–R04 im Detail | Projektgeschichte, kein Ausblick. Auf Nachfrage in den Notizen |
| Literaturvergleiche (RAGTruth, FACTS) | nicht verifiziert |
| Detaillierte Roadmap, Zeitangaben | Retos Vorgabe |
| Schwellen je Modell, MMR, Coverage-Schwelle senken | gemessen und verworfen — gehört in die Notizen, nicht auf eine Folie |

---

## 3 · Vorschlag für den Aufbau

| # | Folie | Kernaussage | Zeit |
|---|---|---|---|
| 1 | Das Versprechen hält | 0 % Halluzination — und wir haben selbst gefunden, warum die Zahl zu gut aussieht (T1) | 0:45 |
| 2 | Vom Raten zum Messen | Kalibrierung gebaut, Ergebnis: Die Messgrundlage ist zu klein — eine Frage sind 14,3 Punkte (T2, T3) | 0:50 |
| 3 | Wo wir ansetzen würden | Rangproblem statt Fundproblem, +17 Punkte Kopfraum; dazu zwei Stufen, die nie blockieren (T4, T5) | 0:50 |
| 4 | Lokale Modelle | Machbar, noch nicht gut genug — und das vorsichtigste Modell ist nicht das beste (T6) | 0:40 |
| 5 | Was als Nächstes dran ist | Erst der Massstab, dann das Gate, dann der Hebel, dann der Betrieb (T7) | 0:35 |
| 6 | Schluss | Der Beleg, dass es hält, ist die eigentliche Arbeit (T8) | 0:20 |

**Summe rund 3:40**, sechs Folien.

**Kurzvariante 2:10**, falls es bei Retos Budget bleibt: Folie 3 entfällt (der Re-Ranker wird
auf Folie 5 ein Satz), Folie 1 auf 0:30, Folie 4 auf die eine Tabellenzeile mit dem
Zielkonflikt, Folie 2 unverändert — sie ist der Kern.

---

## 4 · Die Zeitfrage, die jetzt ansteht

Retos Budget: Block 2 sechs bis sieben Minuten, Block 5 ein bis zwei. Real: Block 2 neun,
Block 5 rund dreieinhalb. Das sind **rund vier Minuten über Plan**, und die müssen irgendwo
herkommen — 30 Minuten stehen fest.

Drei Möglichkeiten, in meiner Reihenfolge:
1. **Aus der Demo.** 8–9 Minuten sind grosszügig; das Quiz ist dort ohnehin als «evtl.
   streichen» markiert. Wird es gestrichen, gewinnt die Demo zwei Minuten — und Block 2 trägt
   die Fragegenerierung sowieso schon.
2. **Block 5 auf die Kurzvariante** (2:10) — dann fällt der Re-Ranker als eigene Aussage weg.
3. **Block 2 auf 7:50** — die drei Kürzungen liegen in `Block2_Notizen.md` bereit.

**Das ist eine Absprache mit Reto, keine Bauentscheidung.** Ich baue Block 5 auf 3:40 und halte
die Kurzvariante im selben Skript bereit.

---

## 5 · Offene Fragen

1. **Wie viel Zeit bekommt Block 5?** Siehe oben. Solange das offen ist, baue ich auf 3:40.
2. **Wie weit gehen wir bei der Halluzinations-Kennzahl (T1)?** Meine Meinung: ganz. Es ist
   unser eigener Befund, er macht die Arbeit glaubwürdiger, nicht schwächer — und wenn er im
   Publikum jemand findet, ist es besser, wir haben ihn zuerst gefunden. **Mit Frank abstimmen**,
   er hat das Eval abgenommen.
3. **Nennen wir die Zahl 2,9 % auf der Folie?** Ich wäre dafür, zusammen mit dem Hinweis, dass
   das für RAG ein guter Wert ist — aber ohne den unverifizierten Literaturvergleich.
4. **Christophs Learnings-Folie** (T-28, zwei Ungenauigkeiten, Details in
   `Archive/Block5_Notizen.md`) — ist das mit ihm besprochen?
5. **Reihenfolge im Block:** Fazit vor Ausblick, wie oben — oder mit den lokalen Modellen
   beginnen, weil sie das Publikum am meisten interessieren? Ich bleibe bei der Reihenfolge
   oben: Erst was hält, dann was fehlt.
