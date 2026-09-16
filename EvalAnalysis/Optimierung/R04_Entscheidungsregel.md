# R04 — Regel 3 und 4 als eine Entscheidung (unvollständig, offen)

> **Status 2026-09-16: Runde begonnen, nicht abgeschlossen.** Gemessen sind `openai`,
> `qwen3-local` und `gpt-oss-local`. `ministral3-local` wurde mitten im Lauf abgebrochen
> (Rechner gebraucht), `gemma4-local` ist nicht gestartet. Solange diese zwei fehlen, ist
> kein Entscheid möglich — die Zahlen unten sind ein Zwischenstand. Fortsetzung: Abschnitt 7.

Vorgehen in `00_Vorgehen.md`, Vorrunden in `R00_Baseline.md`, `R01_Satzzerlegung.md`,
`R02_Zitierformat.md`, `R03_Praemissen.md`. Rohdaten: `kennzahlen.csv` (Zeilen `R04,…`),
`werkzeuge/r03_praemissen.py`, `werkzeuge/vergleich.py`.

## Worum es geht

Zwei Runden haben je eine Hälfte des Problems offengelegt:

- **R00/R03 — Übervorsicht:** Fragen, deren Annahme der Kontext widerlegt («der Belmont-Report
  nennt fünf Prinzipien»), werden verweigert statt richtiggestellt. Eine als Ausnahme
  *angehängte* Regel (R03) hat daran nichts geändert.
- **R00 — Teilantworten auf Fragen ohne Antwort im Korpus:** gemma4 und qwen3 bauen aus
  verwandten Passagen eine Teilantwort mit benannter Lücke. Das ist nach Regel 4 erlaubt, und
  gerade deshalb verfehlen beide die 90-%-Grenze beim Out-of-Corpus-Refusal.

R04 baut deshalb die Regeln 3 und 4 **um** statt sie zu ergänzen.

## 1. Hypothese

> Werden Verweigerung, Richtigstellung und Teilantwort zu **einer** Entscheidung mit drei
> ausdrücklich getrennten Fällen, steigt der Anteil richtiggestellter Annahme-Fragen **und** die
> Out-of-Corpus-Refusal-Rate (weil «Ähnliches zu einem anderen Gegenstand» ausdrücklich keine
> Teilantwort ist), ohne dass die False-Suppression steigt.

## 2. Änderung

Eine Stellschraube: der Regelblock 3/4 des Generierungs-Prompts (`app/services/generation.py`,
Commit `b7246f9`, Test `tests/test_generation.py`).

| vorher (bis R03) | R04 |
|---|---|
| **3.** Deckt der Kontext die Frage nicht ab, antworte ausschliesslich mit WEISS_NICHT — ohne Begründung, ohne weiteren Text.<br>**4.** Ist nur ein Teil der Frage belegt, beantworte diesen Teil und benenne ausdrücklich, was der Kontext nicht abdeckt. | **3.** Entscheide zuerst, welcher der drei Fälle vorliegt:<br>a) Der Kontext **widerlegt eine Annahme** der Frage — etwa eine falsche Anzahl oder eine Regel, die so nicht besteht: stelle die Annahme mit Beleg richtig.<br>b) Der Kontext beantwortet die Frage **ganz oder in einem Teil**: antworte auf diesen Teil.<br>c) Der Kontext trägt zur gestellten Frage **nichts** bei — auch dann nicht, wenn er Ähnliches zu einem anderen Gegenstand enthält: antworte ausschliesslich mit WEISS_NICHT.<br>**4.** Im Fall b) benenne ausdrücklich, was der Kontext nicht abdeckt. |

## 3. Zwischenstand (Vergleichsbasis R03)

Alle 80 Fragen:

| Profil | Out-of-Corpus-Refusal | False-Suppression | Halluzination (Pool) | Lauf |
|---|---|---|---|---|
| `openai` | 90,9 % → 90,9 % | 24,4 % → **22,2 %** | 0 % (41) | 2026-09-16T04-52-06Z / T04-50-07Z |
| `qwen3-local` | 59,1 % → **68,2 %** | 6,7 % → 6,7 % | 0 % | 2026-09-16T05-00-52Z / T04-52-42Z |
| `gpt-oss-local` | 90,9 % → **95,5 %** | 40,0 % → **37,8 %** | 0 % | 2026-09-16T05-19-11Z / T05-03-00Z |
| `ministral3-local` | offen | offen | offen | abgebrochen |
| `gemma4-local` | offen | offen | offen | nicht gestartet |

Entwicklungs-Set:

| Profil | Annahme-Fragen beantwortet | Out-of-Corpus verweigert | False-Suppression | Kontrollfragen |
|---|---|---|---|---|
| `openai` | 4 → **5 von 6** | 15 → 15 von 16 | 7 → **6 von 33** | verweigert (`WEISS_NICHT`) |
| `qwen3-local` | 5 → 5 | 10 → **11 von 16** | 1 → 1 | **`SKOS-ADV-02` in Prosa verweigert** (4.2) |
| `gpt-oss-local` | 3 → 3 (`AIA-ADV-02` inhaltlich richtig, an Coverage 0,33 gescheitert) | 14 → **15 von 16** | 13 → 12 | verweigert |

**Gültigkeit:** alle drei Läufe `finish_reason = stop`, keine leeren Antworten, keine
Endlosschleife (anders als qwen3 in R03).

## 4. Beobachtungen bis hier

### 4.1 Die Richtung stimmt bei allen drei Profilen

Die Refusal-Rate steigt dort, wo sie zu tief war (qwen3 +9 pp, gpt-oss +4,6 pp), und die
False-Suppression sinkt gleichzeitig leicht. Das ist der Gegensatz zu R03, wo nichts passierte —
die Umstellung von «Regel plus Ausnahme» auf «eine Entscheidung mit drei Fällen» ist also der
wirksamere Hebel. Ob das auch für ministral (heute 100 % Refusal, die stärkste Verweigerung) und
gemma4 (81,8 %, das eigentliche Ziel von Fall c) gilt, ist offen.

### 4.2 Verweigerung in Prosa kommt zurück (qwen3)

qwen3 antwortet auf die Kontrollfrage «Stimmt es, dass der Grundbedarf CHF 997 beträgt?»:

> «Die Kontext-Abschnitte enthalten keine Angabe über den konkreten Betrag des Grundbedarfs für
> eine Einzelperson. [1][2][3][4][5]»

Inhaltlich richtig — die Zahl wird nicht bestätigt, nichts erfunden — aber im falschen Format
(Klasse P1 aus R00), mit Scheinbelegen auf alle fünf Abschnitte, und damit ausgeliefert statt
unterdrückt. Der neue Fall c nennt die Verweigerung nicht mehr als erste Anweisung, sondern als
dritte Möglichkeit; ein Zusammenhang ist plausibel, mit einem Lauf aber nicht belegbar.

### 4.3 Die DSGVO-Verwechslung überlebt Fall c

`AIA-OOC-01` («Wie berechnet sich die DSGVO-Bussgeldhöhe?») — nicht im Korpus, der Korpus enthält
die Bussgeldregeln des **AI Act**:

| Profil | R04-Antwort | Bewertung |
|---|---|---|
| `qwen3-local` | «Die DSGVO-Bussgeldhöhe … wird im EU_AI_ACT festgelegt und beträgt bis zu 750 000 EUR [1].» | falsch, belegt aussehend, Coverage 1,0, ausgeliefert |
| `openai` | Kriterien (Art, Schwere, Dauer, KMU-Grösse) ohne Nennung der Rechtsgrundlage | Verwechslung, vorsichtiger formuliert, ausgeliefert |

Fall c war genau für diesen Fall gedacht («auch dann nicht, wenn er Ähnliches zu einem anderen
Gegenstand enthält»), greift aber nicht: Die Modelle behandeln «Bussgelder» als dasselbe Thema.
Damit bleibt der Befund aus R02 bestehen — gegen inhaltliche Verwechslung hilft keine
Formregel, nur eine inhaltliche Prüfung.

## 5. Noch nicht gemacht

- **ministral und gemma4 messen** (ministral ~35 min, gemma4 ~90 min).
- **Einordnung der Abweichungen** für R04 (`labels/R04.csv` existiert nicht).
- **Generierter Bericht** (`berichte/R04_Modellvergleich.md`): bewusst nicht erzeugt —
  `eval.compare` nimmt je Profil den neuesten Lauf und würde R04, R03 und R01 in einer Tabelle
  mischen, solange zwei Profile fehlen.
- **Entscheid** (Regel behalten oder zurücknehmen) und ADR-Nachtrag.

## 6. Risiken für den Entscheid

1. **Prosa-Verweigerung (4.2)** könnte die Refusal-Gewinne bei qwen3 und gemma4 teilweise
   auffressen: eine in Prosa verweigerte Frage zählt als ausgeliefert.
2. **Längerer Prompt:** Der Regelblock ist deutlich länger; bei gpt-oss war schon in R03 zu sehen,
   dass Formattreue unter längeren Anweisungen leidet.
3. **Kein Effekt gegen Verwechslungen (4.3)**, während gleichzeitig mehr Antworten ausgeliefert
   werden — das erhöht die Last auf Stufe 3, die seit R01 seltener läuft.

## 7. So wird fortgesetzt

Stack starten (`make up`, aus `src/`), Ollama läuft lokal, dann im `api`-Container:

```bash
# 1. fehlende Profile messen, Code-Stand b7246f9 (nicht ändern!)
docker exec src-api-1 sh -c 'rm -f /tmp/eval-chain.log'
docker exec -d -e EVAL_GIT_SHA=b7246f9 src-api-1 sh /tmp/chain.sh ministral3-local gemma4-local

# 2. auswerten (Fenster: R03 = 2026-09-15T21-36…2026-09-16T04, R04 = ab 2026-09-16T04-50)
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r03_praemissen.py \
  2026-09-15T21-36 2026-09-16T04 2026-09-16T04-50 9999
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/vergleich.py \
  2026-09-15T21-36 2026-09-16T04 2026-09-16T04-50 9999
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r02_format.py R04 2026-09-16T04-50
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/kennzahlen_runde.py R04 2026-09-16T04-50
docker exec -w /app src-api-1 python -m eval.compare > ../EvalAnalysis/Optimierung/berichte/R04_Modellvergleich.md
```

Die Skripte liegen im Repo unter `werkzeuge/` und müssen vorher einmal in den Container kopiert
werden (`docker cp`, siehe `werkzeuge/README.md`); `holdout.json` gehört nach `/tmp/holdout.json`.
Die drei bereits gemessenen Läufe bleiben gültig — sie liegen unter
`src/backend/eval/out/<profil>/…2026-09-16T04-5*` bzw. `T05-*` (lokal, gitignored).

**Wichtig:** Am Prompt bis zum Abschluss der Runde nichts ändern, sonst sind die fünf Läufe nicht
mehr vergleichbar.

## Nachträge

*(noch keine)*
