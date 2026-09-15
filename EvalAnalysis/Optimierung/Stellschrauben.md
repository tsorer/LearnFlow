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
