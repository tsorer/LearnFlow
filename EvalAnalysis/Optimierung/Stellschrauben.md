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
