# Modell-Steckbriefe

Laufend ergänzt, eine Zeile Beobachtung je Runde. Kennzahlen stehen in `kennzahlen.csv`,
nicht hier.

## Übersicht

| Profil | Modell | Anbieter | Grösse / Architektur | Denkmodus | Status |
|---|---|---|---|---|---|
| `openai` | gpt-4o-mini | OpenAI (Cloud) | nicht veröffentlicht | nein | Referenz |
| `qwen3-local` | qwen3:8b | Alibaba | 8 B, dicht | abgeschaltet (`think: false`) | aktiv |
| `gemma4-local` | gemma4:26b | Google | 26 B, MoE | ja, nicht abschaltbar | **pausiert** ab R02 (bis R04) |
| `gpt-oss-local` | gpt-oss:20b | OpenAI (open weight) | 21 B, MoE (~3,6 B aktiv) | ja, Stufe `low` | aktiv |
| `ministral3-local` | ministral-3:14b | Mistral (EU) | 14 B, dicht | nein | aktiv |

## Profilparameter

Alle lokalen Profile: `api_base` Ollama, `api_key: None`, `num_ctx: 16384`,
`timeout_seconds: 1800`, `max_answer_tokens: 8000`, `self_check_timeout_seconds: 600`.

| Profil | `max_verdict_tokens` | Besonderheit |
|---|---|---|
| `qwen3-local` | 1000 | `think: false` — sonst ~53 s Nachdenken je Aufruf bei gleicher Antwort |
| `gemma4-local` | 4000 (seit R00, vorher 1000) | 1000 reichte bei In-Corpus-Kontexten nicht für den Self-Check |
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

### `qwen3-local` — qwen3:8b

- **R00:** Verweigert in Prosa statt mit `WEISS_NICHT` (P1) und hängt das Sentinel teils
  an den Text (P3). Liefert am meisten aus (False-Suppression 6,7 %), verweigert
  Out-of-Corpus-Fragen am schlechtesten (68,2 %). Ein inhaltlicher Fehler (S3), vom
  Self-Check gefangen.
- **R01:** Unverändert (False-Suppression 1/33); drei Antworten überspringen den Self-Check jetzt,
  weil ihre Coverage korrekt auf 1,0 steigt. 72 von 80 Antworten wortgleich zu R00.

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

### `gpt-oss-local` — gpt-oss:20b

- **R00:** Formatprobleme dominieren: Sammelbeleg (7×), vollbreite Klammern `【1】`,
  Buchstabenverweise `[f][g]`. Höchste False-Suppression (48,9 %). Einmal Self-Check-
  Fehlurteil bei korrekter Antwort. Schnellstes lokales Modell, reproduzierbar.
- **R01:** Nur 48 von 80 Antworten wortgleich zu R00 — über Tage **nicht** reproduzierbar. Reine
  R01-Wirkung −2. Einmal inhaltlich falsche Antwort ausgeliefert (`AIA-ANFORDERUNGEN-02`, Self-Check
  `GEDECKT`), einmal erfundene Referenz `[13]` korrekt gestoppt.

### `ministral3-local` — ministral-3:14b

- **R00:** Einziges Modell mit 100 % Out-of-Corpus-Refusal. Belegt mit Unterverweisen auf
  Absätze im Chunk (`[1a]`, `[1.2b]`, `[1(3a)]`, 6×) — inhaltlich präzise, von der Pipeline
  nicht erkannt. Schreibt `WEISS_NICHT, ob …` in den Fliesstext (P3). Strukturiert
  Antworten mit Überschriften und Abschnitt «Nicht abgedeckt», was die Segmentierung von
  Stufe 2 trifft (S2c, S2d).
- **R01:** Grösster Gewinner (False-Suppression Dev 13 → 10). Self-Check lehnte drei Antworten ab,
  die dank R01 Stufe 2 neu passierten — darunter eine inhaltlich falsche und eine
  Out-of-Corpus-Frage; 100 % Refusal bleiben.
