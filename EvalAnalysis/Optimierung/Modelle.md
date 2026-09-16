# Modell-Steckbriefe

Laufend ergänzt, eine Zeile Beobachtung je Runde. Kennzahlen stehen in `kennzahlen.csv`,
nicht hier.

## Übersicht

| Profil | Modell | Anbieter | Grösse / Architektur | Denkmodus | Status |
|---|---|---|---|---|---|
| `openai` | gpt-4o-mini | OpenAI (Cloud) | nicht veröffentlicht | nein | Referenz |
| `qwen3-local` | qwen3:8b | Alibaba | 8 B, dicht | abgeschaltet (`think: false`) | aktiv |
| `gemma4-local` | gemma4:26b | Google | 26 B, MoE | ja, nicht abschaltbar | aktiv (Pause R02–R03, seit R04 wieder) |
| `gpt-oss-local` | gpt-oss:20b | OpenAI (open weight) | 21 B, MoE (~3,6 B aktiv) | ja, Stufe `low` | aktiv |
| `ministral3-local` | ministral-3:14b | Mistral (EU) | 14 B, dicht | nein | aktiv |

## Profilparameter

Alle lokalen Profile: `api_base` Ollama, `api_key: None`, `num_ctx: 16384`,
`timeout_seconds: 1800`, `self_check_timeout_seconds: 600`, `max_answer_tokens: 8000` —
ausser `gemma4-local`, siehe unten.

| Profil | `max_verdict_tokens` | Besonderheit |
|---|---|---|
| `qwen3-local` | 1000 | `think: false` — sonst ~53 s Nachdenken je Aufruf bei gleicher Antwort |
| `gemma4-local` | 4000 (seit R00, vorher 1000) | 1000 reichte bei In-Corpus-Kontexten nicht für den Self-Check; `max_answer_tokens` seit R05 12000 statt 8000 (R04: zwei Antworten liefen ins Limit) |
| `gpt-oss-local` | 1000 | `think: "low"` — `think: false` ignoriert Ollama für dieses Modell |
| `ministral3-local` | 1000 | – |

## Testhardware

| Profil | Ollama-Grösse | CPU/GPU bei `num_ctx` 16384 |
|---|---|---|
| `qwen3-local` | 5,2 GB | 20 % / 80 % (geladen 7,8 GB inkl. Kontextspeicher) |
| `gemma4-local` | 18 GB | 24 % / 76 % laut `ollama ps` — Anzeige unplausibel (meldet 1,3 GB geladen) |
| `gpt-oss-local` | 13 GB | 58 % / 42 % |
| `ministral3-local` | 9,1 GB | 50 % / 50 % |

Kein lokales Modell passt mit 16K-Kontext vollständig in die 8 GB VRAM der Testhardware.

## Beobachtungen je Runde

### `openai` — gpt-4o-mini

- **R00:** Belegt gesammelt am Absatz- oder Listenende (S2a, 5×). Verweigert Ja/Nein-Fragen,
  die eine Schlussfolgerung verlangen, und Fragen mit falscher Prämisse (S1, 6×). Nicht
  reproduzierbar trotz Temperatur 0.
- **R01:** Keine Wirkung der neuen Satzzerlegung auf Unterdrückungen; 15 von 80 Antworten anders
  als in R00 (Rauschen). Self-Check läuft seltener (Dev 20 → 15).
- **R02a:** Präziserer Prompt senkt unbelegte Aussagen 41 % → 28 % und False-Suppression Dev 10 → 8;
  in fast jeder zweiten Antwort bleibt aber irgendwo ein Sammelbeleg.
- **R03:** Regel-Ausnahme für falsche Annahmen ohne Wirkung (4 von 6 Annahme-Fragen wie vorher);
  False-Suppression Dev 8 → 7.
- **R04:** Annahme-Fragen 4 → 5 von 6 (neu `SAMW-ADV-01`), False-Suppression Dev 7 → 6, Refusal
  unverändert 90,9 %. Antworten werden länger (342 → 426 Zeichen bei gleich vielen Belegen),
  unbelegte Aussagen 27 % → 31 %. Liefert neu die DSGVO-Frage `AIA-OOC-01` mit AI-Act-Kriterien
  aus (F1) — Stufe 3 urteilt dort `GEDECKT`, weil die Kriterien im Kontext stehen; nur die Frage
  war eine andere.

### `qwen3-local` — qwen3:8b

- **R00:** Verweigert in Prosa statt mit `WEISS_NICHT` (P1) und hängt das Sentinel teils
  an den Text (P3). Liefert am meisten aus (False-Suppression 6,7 %), verweigert
  Out-of-Corpus-Fragen am schlechtesten (68,2 %). Ein inhaltlicher Fehler (S3), vom
  Self-Check gefangen.
- **R01:** Unverändert (False-Suppression 1/33); drei Antworten überspringen den Self-Check jetzt,
  weil ihre Coverage korrekt auf 1,0 steigt. 72 von 80 Antworten wortgleich zu R00.
- **R02a:** Belegt jetzt fast alles (7 % unbelegt) — auch falsche Antworten: DSGVO-Frage mit AI-Act-Kriterien
  beantwortet und ausgeliefert. Out-of-Corpus-Refusal 68 % → 59 %.
- **R03:** Keine Wirkung auf Annahme-Fragen (5 von 6). Einmal in einer Endlosschleife hängen
  geblieben (`AIA-OOC-01`, 8000 Tokens, 13 min, als abgeschnitten unterdrückt).
- **R04:** Grösster Refusal-Gewinn der Runde (59,1 % → 68,2 %) bei unveränderter
  False-Suppression (6,7 %) — bleibt damit trotzdem weit unter der 90-%-Grenze. Die
  Prosa-Verweigerung (P1) kommt zurück, neu auch auf der Kontrollfrage `SKOS-ADV-02`, jeweils
  mit Scheinbelegen `[1][2][3][4][5]` und damit Coverage 1,0: eine Verweigerung, die formal
  wie eine perfekt belegte Antwort aussieht. `AIA-OOC-01` weiterhin falsch beantwortet
  («DSGVO-Bussgeld … wird im EU_AI_ACT festgelegt», F1).

### `gemma4-local` — gemma4:26b

- **R00:** Protokolltreuestes Modell (98,3 %). Verfehlt die 90-%-Grenze beim Out-of-Corpus-Refusal
  ausschliesslich mit richtigen Urteilen: Teilantworten mit benannter Lücke (P2) — genau
  das, was Regel 4 verlangt — und dem Gold-Fehler `SAMW-OOC-03`. Sehr langsam auf der
  Testhardware; hoher unsichtbarer Denkanteil (bis 5400 Tokens je Aufruf).
- **R01:** Profitiert wie vorhergesagt (False-Suppression Dev 4 → 2). Einziges Modell mit 80 von 80
  wortgleichen Antworten über zwei Tage. 86 min LLM-Zeit, rund 60 % der Rundendauer;
  Pausierung zur Diskussion gestellt.
- **Entscheid 2026-09-15:** pausiert für R02 und R03, Wiederaufnahme für R04 (Regel 3 vs. Regel 4).
  Begründung: 86 min LLM-Zeit je Runde (rund 60 %), als Produktivmodell wegen Laufzeit und
  Hardwarebedarf kaum Chancen; zentral bleibt es für die Frage Teilantwort vs. Verweigerung.
- **R04** (Vergleichsbasis R01, enthält also auch R02a): bestes Profil auf beiden Achsen —
  Urteilsfähigkeit 0,983, Protokolltreue **1,000**, 6 von 6 Annahme-Fragen, Refusal
  81,8 % → 86,4 %. Belegdichte verbessert sich (unbelegte Aussagen 10 % → 7 %), weil R02a hier
  zum ersten Mal wirkt. Der lange Regelblock verdoppelt aber den unsichtbaren Denkanteil
  (Median 858 → 1535 Completion-Tokens, 2,43 → 4,11 Tokens je sichtbarem Zeichen); zwei Fragen
  laufen ins Token-Limit und kommen leer zurück (Klasse A) → `max_answer_tokens` ab R05 12000.
- **Entscheid 2026-09-16:** Pause aufgehoben, bleibt in der Reihe. Trotz 2 h 13 min Laufzeit je
  Runde der aussichtsreichste lokale Kandidat; Laufzeit ist laut `00_Vorgehen.md` kein
  Ausschlusskriterium.

### `gpt-oss-local` — gpt-oss:20b

- **R00:** Formatprobleme dominieren: Sammelbeleg (7×), vollbreite Klammern `【1】`,
  Buchstabenverweise `[f][g]`. Höchste False-Suppression (48,9 %). Einmal Self-Check-
  Fehlurteil bei korrekter Antwort. Schnellstes lokales Modell, reproduzierbar.
- **R01:** Nur 48 von 80 Antworten wortgleich zu R00 — über Tage **nicht** reproduzierbar. Reine
  R01-Wirkung −2. Einmal inhaltlich falsche Antwort ausgeliefert (`AIA-ANFORDERUNGEN-02`, Self-Check
  `GEDECKT`), einmal erfundene Referenz `[13]` korrekt gestoppt.
- **R02a:** Grösster Gewinner des Prompts: fremde Formate 5 % → 0 %, unbelegte Aussagen 56 % → 41 %,
  False-Suppression Dev 14 → 8.
- **R03:** Annahme-Fragen 3 → 4 (nur `SAMW-ADV-04`); False-Suppression Dev 8 → 13 durch
  Formatrauschen (unbelegte Aussagen 41 % → 49 %). Instabilstes Modell der Reihe.
- **R04:** Höchste Refusal-Rate der Reihe (90,9 % → 95,5 %) und Urteilsfähigkeit 0,948 — aber
  unverändert die schlechteste Protokolltreue (0,810) und mit 37,8 % die höchste
  False-Suppression. Unbelegte Aussagen 49 % → 57 %, in `SKOS-SIL-01` (3244 Zeichen) **kein
  einziger** Beleg. Annahme-Fragen 4 → 3, nicht weil das Urteil kippt, sondern weil
  `AIA-ADV-02` an Coverage 0,33 scheitert.

### `ministral3-local` — ministral-3:14b

- **R00:** Einziges Modell mit 100 % Out-of-Corpus-Refusal. Belegt mit Unterverweisen auf
  Absätze im Chunk (`[1a]`, `[1.2b]`, `[1(3a)]`, 6×) — inhaltlich präzise, von der Pipeline
  nicht erkannt. Schreibt `WEISS_NICHT, ob …` in den Fliesstext (P3). Strukturiert
  Antworten mit Überschriften und Abschnitt «Nicht abgedeckt», was die Segmentierung von
  Stufe 2 trifft (S2c, S2d).
- **R01:** Grösster Gewinner (False-Suppression Dev 13 → 10). Self-Check lehnte drei Antworten ab,
  die dank R01 Stufe 2 neu passierten — darunter eine inhaltlich falsche und eine
  Out-of-Corpus-Frage; 100 % Refusal bleiben.
- **R02a:** Unterverweise `[1a]` fast verschwunden (24 % → 3 %), unbelegte Aussagen 36 % → 21 %. Neue
  Fehlerform: zitiert Erwägungsgrund-Nummern des AI Act (`[13]`, `[65]`) statt der Abschnittsnummer.
- **R03:** Annahme-Fragen 2 → 3 (nur `SAMW-ADV-04`); False-Suppression Dev 9 → 8, 100 % Refusal.
- **R04:** Einziges Profil, das sich verschlechtert (False-Suppression 31,1 % → 40,0 %,
  Annahme-Fragen 3 → 2). Ursachenkette: längere Antworten bei weniger Belegen (539 → 655 Zeichen,
  Median-Belege 4 → 3, unbelegte Aussagen 16 % → 27 %) → Coverage fällt reihenweise von 1,0 auf
  0,5–0,85 → Stufe 3 läuft 6× statt 16× → **und ministrals Self-Check urteilt dort systematisch
  falsch**: 8 von 16 Urteilen `NICHT_GEDECKT`, davon 5 als S4 eingeordnet, weil das Modell
  auflistet, was in der Antwort *fehlt*, statt zu prüfen, ob das Gesagte gedeckt ist. Alle anderen
  Profile zusammen: ein einziges `NICHT_GEDECKT`. Damit ist ministral der Auslöser für R05
  (Self-Check-Prompt). Refusal 100 % → 95,5 %, aber nur wegen der Gold-Fehlfrage `SAMW-OOC-03`.
