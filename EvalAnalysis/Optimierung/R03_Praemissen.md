# R03 — Falsche Annahmen korrigieren statt verweigern (verworfen)

Dritte Optimierungsrunde, **Negativergebnis**. Die geprüfte Prompt-Regel ist nach der Messung
wieder entfernt worden (`git revert`, Commit `0f9d9aa`). Dieses Dokument ist ohne weitere
Dokumente lesbar; Vorgehen in `00_Vorgehen.md`, Vorrunden in `R00_Baseline.md`,
`R01_Satzzerlegung.md`, `R02_Zitierformat.md`. Rohdaten: `kennzahlen.csv`,
`berichte/R03_Modellvergleich.md`, `werkzeuge/r03_praemissen.py`, `werkzeuge/vergleich.py`.

## Worum es geht

LearnFlow antwortet nur aus hochgeladenen Dokumenten und ist **fail-closed**: Deckt der Kontext
die Frage nicht, soll das Modell mit dem Codewort `WEISS_NICHT` verweigern (Regel 3 des
Generierungs-Prompts), statt etwas zu erfinden.

Die Baseline R00 zeigte eine Gegenrichtung: **Übervorsicht.** Fragen, deren Antwort im Kontext
steht, wurden verweigert — besonders auffällig bei Fragen mit **falscher Annahme**, etwa

- «Auf welcher Seite formuliert der Leitfaden das absolute Verbot …?» — der Leitfaden nennt
  diesen Satz ausdrücklich nur als **Gegenbeispiel** (`SAMW-ADV-01`);
- «Der Belmont-Report nennt fünf Prinzipien — wie lauten alle fünf?» — es sind **drei**
  (`SAMW-ADV-02`);
- «Hat die Schweiz das Zusatzprotokoll ratifiziert?» — es wurde **nicht unterzeichnet**
  (`SAMW-ADV-04`).

Der Prompt kannte für solche Fragen keinen Weg: antworten (Regeln 1, 2, 4) oder `WEISS_NICHT`
(Regel 3). Die Modelle wählten die Verweigerung.

| Begriff | Bedeutung |
|---|---|
| **Entwicklungs-Set (Dev)** | 58 der 80 Gold-Fragen; 22 (Holdout) bleiben bis zur Schlussrunde unausgewertet |
| **False-Suppression** | Anteil unterdrückter Fragen, deren Antwort im Korpus steht — tiefer ist besser |
| **Out-of-Corpus-Refusal** | Anteil korrekt verweigerter Fragen ohne Antwort im Korpus — höher ist besser |
| **Annahme-Fragen** | die sechs adversarial-Fragen im Dev-Set, deren Prämisse der Kontext widerlegt: `AIA-ADV-01/02/03`, `SAMW-ADV-01/02/04` |
| **Kontrollfragen** | müssen weiter verweigert werden: `SKOS-ADV-02` (suggestiv vorgegebene Zahl «CHF 997»), `SKOS-IPV-02`, alle Out-of-Corpus-Fragen |

## Kernaussage

> **Eine als Ausnahme angehängte Regel überwindet die Verweigerungspräferenz nicht.** Von den
> sechs Annahme-Fragen wurden nach der Änderung genau **eine** mehr beantwortet (gpt-oss und
> ministral je `SAMW-ADV-04`) — unter der Auflösung dieser Runde. Die beiden Fragen mit der
> klarsten Widerlegung im Kontext (`SAMW-ADV-01`, `SAMW-ADV-02`) blieben bei allen Modellen
> `WEISS_NICHT`. Die Regel ist deshalb wieder entfernt: Sie verlängert den Prompt, ohne etwas
> zu bewegen. Lehrreich ist die Stelle, an der sie stand — hinter «antworte **ausschliesslich**
> mit WEISS_NICHT». Ein Nachsatz relativiert diese Anweisung offenbar nicht; R04 muss Regel 3
> und Regel 4 umbauen, nicht ergänzen.

| Profil | Annahme-Fragen beantwortet R02a → R03 | False-Suppression Dev | Out-of-Corpus Dev | Kontrollfragen |
|---|---|---|---|---|
| `openai` | 4 → 4 von 6 | 8 → 7 | 16 → 15¹ | unverändert verweigert |
| `qwen3-local` | 5 → 5 | 0 → 1 | 9 → 10² | unverändert verweigert |
| `gpt-oss-local` | 3 → **4** | 8 → **13** | 14 → 14 | unverändert verweigert |
| `ministral3-local` | 2 → **3** | 9 → 8 | 16 → 16 | unverändert verweigert |

¹ `SAMW-OOC-03` — die Frage mit dem Fehler im Gold-Dataset (R00, Befund 5.1), die zwischen
ausgeliefert und verweigert pendelt. ² Kein Gewinn, sondern ein Artefakt (Abschnitt 5.2).

## 1. Hypothese

> Bekommt der Prompt eine Regel für Fragen mit falscher Annahme — «stelle die Annahme mit Beleg
> richtig, statt zu verweigern» —, beantworten die Modelle die sechs Annahme-Fragen häufiger
> richtig. Kontrollfragen (Annahme vom Kontext weder bestätigt noch widerlegt) bleiben verweigert,
> Out-of-Corpus-Refusal und Halluzinationsrate bleiben unverändert.

**Erwarteter Effekt:** +1 bis +3 Annahme-Fragen je Modell, keine Verschlechterung der
Kontrollfragen.

## 2. Was geändert wurde

Eine Stellschraube: **Regel 3 des Generierungs-Prompts** (`app/services/generation.py`, Commit
`997f08b`, Test in `tests/test_generation.py`, beide inzwischen zurückgenommen).

| vorher | nachher (nur für diese Runde) |
|---|---|
| Deckt der Kontext die Frage nicht ab, antworte ausschliesslich mit WEISS_NICHT — ohne Begründung, ohne weiteren Text. | … ohne weiteren Text. **Ausnahme: Beruht die Frage auf einer Annahme, die der Kontext ausdrücklich widerlegt — etwa eine falsche Anzahl oder eine Regel, die so nicht besteht —, stelle die Annahme mit Beleg richtig. Bestätigt der Kontext die Annahme nicht und widerlegt er sie auch nicht, bleibt es bei WEISS_NICHT.** |

**Bewusst eng gehalten:** «ausdrücklich widerlegt», plus der zweite Satz als Schutz. Ohne ihn
hätte die Regel eine Einladung zum Erfinden sein können — genau bei Fragen wie «Stimmt es, dass
der Grundbedarf CHF 997 beträgt?», wo der Kontext die Zahl weder bestätigt noch widerlegt
(die Betragstabelle fehlt im eingelesenen PDF-Text).

**Eine geplante zweite Änderung wurde vor der Messung gestrichen.** Ursprünglich sollte die Runde
auch Ja/Nein-Fragen adressieren (`SKOS-EL-01` «Gehen Ergänzungsleistungen der Sozialhilfe vor?»,
`SKOS-IPV-01` «Muss man die IPV beanspruchen?»). Die Prüfung der Kontext-Abschnitte zeigte: Die
tragende Aussage steht dort **nicht** — der Vorrang bzw. die Pflicht zur Geltendmachung steht auf
Seiten, die das Retrieval nicht geliefert hat. Eine Regel «schliesse bei Ja/Nein-Fragen aus dem
Kontext» hätte hier Halluzinationen belohnt. Siehe Abschnitt 5.4.

## 3. Messung

- **Live-Lauf** aller vier aktiven Profile auf Commit `997f08b` (gemma4 ist für R02/R03
  pausiert), Vergleichsbasis ist R02a.
- **Zielgrösse** ist nicht die False-Suppression, sondern die sechs Annahme-Fragen: Wird die
  Annahme mit Beleg richtiggestellt (ausgeliefert) oder weiter verweigert? Dazu der Wortlaut
  jeder Antwort, geprüft von Hand (`werkzeuge/r03_praemissen.py`).
- **Kontrollgrössen:** `SKOS-ADV-02`, `SKOS-IPV-02`, alle 16 Out-of-Corpus-Fragen im Dev-Set.
- **Zuordnung:** Wie in R02 ändert die Prompt-Änderung die Antworten selbst; Wirkung und Rauschen
  sind pro Frage nicht trennbar (lokale Modelle sind nur innerhalb einer Sitzung reproduzierbar,
  R01). Deshalb zählt hier der gezielte Blick auf sechs Fragen, nicht die Gesamtrate.

**Gültigkeit:** openai, gpt-oss und ministral: alle Aufrufe `finish_reason = stop`, keine leeren
Antworten. **qwen3: ein Aufruf mit `length`** (Abschnitt 5.2) — der Lauf ist damit nach den
Kriterien aus `00_Vorgehen.md` streng genommen ungültig; die Behandlung ist dort begründet.

## 4. Ergebnis im Detail

### 4.1 Die sechs Annahme-Fragen (Dev)

`✓` = Annahme mit Beleg richtiggestellt und ausgeliefert · `✗` = `WEISS_NICHT`

| Frage | openai R02a → R03 | qwen3 | gpt-oss | ministral |
|---|---|---|---|---|
| `AIA-ADV-01` EU-Sitz | ✓ → ✓ | ✓ → ✓ | ✓ → ✓ | ✗ → ✗ (Coverage 0,0 — Beleg `[2a]`) |
| `AIA-ADV-02` Anhang III | ✓ → ✓ | ✓ → ✓ | ✓ → ✓ (Begründung falsch, 5.3) | ✓ → ✓ |
| `AIA-ADV-03` Dokumentation | ✓ → ✓ | ✓ → ✓ | ✓ → ✓ | ✓ → ✓ |
| `SAMW-ADV-01` Verbot | ✗ → ✗ | ✗ → ✗ | ✗ → ✗ | ✗ → ✗ |
| `SAMW-ADV-02` fünf Prinzipien | ✗ → ✗ | ✓ → ✓ | ✗ → ✗ | ✗ → ✗ |
| `SAMW-ADV-04` Ratifikation | ✓ → ✓ | ✓ → ✓ | ✗ → **✓** | ✗ → **✓** |
| **Summe** | 4 → 4 | 5 → 5 | 3 → **4** | 2 → **3** |

Die drei `AIA-ADV`-Fragen beantworteten die Modelle schon vor R03 richtig — sie brauchten die
Regel nicht. Bewegt hat sich nur `SAMW-ADV-04`, bei zwei Modellen, also je eine Frage. Nach
`00_Vorgehen.md` gilt ein Unterschied von einer Frage nicht als Effekt.

### 4.2 Gesamtkennzahlen (alle 80 Fragen)

| Profil | Out-of-Corpus-Refusal R02a → R03 | False-Suppression R02a → R03 | Halluzination (Pool) |
|---|---|---|---|
| `openai` | 95,5 % → 90,9 % | 28,9 % → **24,4 %** | 0 % (40) |
| `qwen3-local` | 59,1 % → 59,1 % | 4,4 % → 6,7 % | 0 % (51) |
| `gpt-oss-local` | 90,9 % → 90,9 % | 28,9 % → **40,0 %** | 0 % (33) |
| `ministral3-local` | 100 % → 100 % | 31,1 % → 31,1 % | 0 % (35) |

Die Bewegungen gehen in beide Richtungen und sind nicht der Regel zuzuschreiben: bei openai und
ministral verändert sich die Zielgrösse nicht, bei gpt-oss verschlechtert sich die
False-Suppression um 5 Fragen (Abschnitt 5.1).

## 5. Beobachtungen

### 5.1 gpt-oss unterdrückt mehr — Formatrauschen, kein R03-Effekt

Bei gpt-oss steigt die False-Suppression im Dev-Set von 8 auf 13. Alle betroffenen Antworten
haben einen **anderen Text** als in R02a, und die neuen Unterdrückungen sind Coverage-Fälle mit
plötzlich null Belegen (`SKOS-PRINZ-01` 1,0 → 0,0; `SAMW-JUGENDLICHE-01` 1,0 → 0,0;
`SAMW-NUERNBERG-01` 1,0 → 0,0). Der Anteil unbelegter Aussagen springt von 41 % auf 49 %. Das ist
dasselbe Rauschen wie in R01/R02: gpt-oss ist das instabilste Modell der Reihe (in R01 nur 48 von
80 Antworten wortgleich zum Vortag). Ein Zusammenhang mit einer Regel, die nur den
Verweigerungsfall betrifft, ist nicht erkennbar — ein Nutzen, der den längeren Prompt trägt,
aber auch nicht.

### 5.2 qwen3 in der Endlosschleife — neue Artefaktform

Bei `AIA-OOC-01` («Wie berechnet sich die DSGVO-Bussgeldhöhe?») wiederholte qwen3 13 Minuten lang
denselben Satz («Die Verjährungsfristen für die Geldbußen sind im Einklang mit dem Grundsatz der
Verhältnismäßigkeit [3]»), bis das Budget von 8000 Tokens erreicht war: `finish_reason = length`,
8000 Completion-Tokens, 775 s. Die Pipeline hat die Antwort korrekt als abgeschnitten unterdrückt
(`generation_truncated`) — dadurch zählt die Frage als «richtig verweigert» und die
Out-of-Corpus-Rate im Dev-Set steigt von 9 auf 10, **ohne dass das Modell besser geworden ist**.

**Behandlung:** Anders als beim gemma4-Artefakt in R00 hilft ein grösseres Budget hier nicht — das
Budget war nicht zu klein, das Modell ist entgleist. Ein Wiederholungslauf würde dieselbe Frage
neu würfeln, nicht die Ursache beheben. Der Lauf bleibt deshalb gültig, die Frage ist als Artefakt
markiert und geht nicht in die Bewertung ein. Das ist eine Abweichung von Kriterium 1 in
`00_Vorgehen.md` und hier ausdrücklich begründet, nicht stillschweigend.

### 5.3 Ein belegter Widerspruch mit falscher Begründung

gpt-oss zu `AIA-ADV-02` («Sind Anhang-III-Systeme immer hochriskant?»):

> Nein. Systeme, die in Anhang III aufgeführt sind, gelten **nur dann** als hochriskant, **wenn**
> sie die in Artikel 6 Absatz 3 genannten Bedingungen erfüllen. Ist dies nicht der Fall, gelten
> sie nicht als hochriskant. [2]

Die Prämisse wird korrekt verneint, die Begründung ist aber verdreht: Artikel 6 Absatz 3 nennt die
**Ausnahmen** von der Hochrisiko-Einstufung. Die Antwort ist formal einwandfrei belegt, Coverage
0,5, und wurde ausgeliefert. Keine automatische Prüfung erkennt das — dieselbe Klasse wie der
Befund aus R02 (Formtreue ist nicht inhaltliche Richtigkeit).

### 5.4 Korrektur der R00-Einordnung (`SKOS-EL-01`, `SKOS-IPV-01`)

R00 hatte diese beiden Verweigerungen als **S1 (Übervorsicht)** eingeordnet, weil die im
Gold-Dataset erwartete Seite im Kontext lag. Die Prüfung der Chunk-Texte für R03 zeigt: Die
tragende Aussage steht dort nicht.

| Frage | Was im Kontext steht | Was fehlt |
|---|---|---|
| `SKOS-EL-01` «Gehen EL der Sozialhilfe vor?» | S. 97: EL kompensieren die Rentenkürzung, EL können beantragt werden | der **Vorrang** (S. 6 / 83: kein Wahlrecht, anrechenbare Einnahme) |
| `SKOS-IPV-01` «Muss man die IPV beanspruchen?» | S. 57: es **besteht ein Anspruch** auf Prämienverbilligung | die **Pflicht**, ihn geltend zu machen (Subsidiarität, S. 6 / 14) |

Beide sind damit **S5 (Retrieval)** und keine Übervorsicht: Die Verweigerung ist vertretbar. Die
sechs betroffenen Zeilen in `labels/R00.csv` sind korrigiert (Klasse S5, Urteil «vertretbar»,
Begründung mit Hinweis «Korrektur R03»), die Kennzahlen neu gerechnet. Auswirkung auf R00:

| Profil | Urteilsfähigkeit vorher → nachher | S1-Fälle | S5-Fälle |
|---|---|---|---|
| `openai` | 89,7 % → **93,1 %** | 6 → 4 | 0 → 2 |
| `gpt-oss-local` | 86,2 % → **89,7 %** | 5 → 3 | 2 → 4 |
| `ministral3-local` | 86,2 % → **89,7 %** | 5 → 3 | 2 → 4 |
| `qwen3-local`, `gemma4-local` | unverändert | unverändert | unverändert |

Die Kernaussage von R00 bleibt: 12 statt 18 Fälle echter Übervorsicht, und der Formatanteil an der
False-Suppression wird dadurch noch grösser.

## 6. Entscheid

| Frage | Entscheid | Begründung |
|---|---|---|
| Regel behalten? | **nein, zurückgenommen** (`git revert`, `0f9d9aa`) | Wirkung eine Frage bei zwei Modellen, unter der Auflösung der Runde; die klarsten Zielfragen bewegen sich nicht. Ein längerer Prompt ohne Wirkung ist ein Nachteil: mehr Tokens, mehr Raum für Fehlinterpretation |
| Modelle | keine Änderung | qwen3 bleibt unter der 90-%-Grenze; gemma4 bleibt pausiert bis R04 |
| Lehre für R04 | Regel 3 und 4 **umbauen**, nicht ergänzen | Die Ausnahme stand hinter «antworte ausschliesslich mit WEISS_NICHT» und wurde überlesen. R04 (Verweigerung gegen Teilantwort) muss die Reihenfolge und Priorität der Regeln selbst ändern und die Annahme-Fragen mitmessen |
| Offene Risiken | unverändert an R04 / Kalibrierung | Formtreue ohne inhaltliche Prüfung (5.3, R02 5.1); Self-Check-Band seit R01 (T-57); Endlosschleifen als Artefaktform (5.2) |

**Was diese Runde trotzdem gebracht hat:** eine belastbare Negativaussage über die Wirkung von
Prompt-Ausnahmen, eine korrigierte Einordnung zweier R00-Fälle, und eine neue Artefaktform, die in
die Gültigkeitsprüfung jeder künftigen Runde gehört.

## Nachträge

*(noch keine)*
