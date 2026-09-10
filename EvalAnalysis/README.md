# EvalAnalysis

Ergebnisse der Eval-Messreihen und ihre Einordnung. Was hier liegt, ist
**Evidenz für** Entscheide, nicht der Entscheid selbst — der gehört nach
`Docs/` (ADR-008 Schwellen, ADR-009 Eval-Strategie).

## Zwei Dateien je Messreihe

| Datei | Herkunft | Anfassen? |
|---|---|---|
| `<datum>_Modellvergleich.md` | generiert aus `eval/out/` | **nein** |
| `<datum>_Befunde.md` | von Hand geschrieben | ja |

Die Trennung hat denselben Grund wie bei `src/frontend/src/api/schema.d.ts`:
eine generierte Datei von Hand zu ergänzen heisst, die Ergänzung beim nächsten
Lauf zu verlieren. Der Vergleich trägt die Zahlen, die Befunde tragen, was sie
bedeuten — und nur letztere sind ein Review wert.

## Einen Bericht erzeugen

Voraussetzung ist ein Lauf je Profil, denn `make eval` misst immer nur eines
(`EVAL_PROFILE`, siehe `Ops/09_CI-Runbook.md`):

```bash
make up && make seed && make seed-corpus
make eval                                # ausgeliefertes Profil — das Gate
make eval EVAL_PROFILE=qwen3-local
make eval EVAL_PROFILE=gemma4-local

docker exec src-api-1 python -m eval.compare > EvalAnalysis/$(date +%F)_Modellvergleich.md
```

`eval/compare.py` liest je Profil den **neuesten** Lauf unter
`src/backend/eval/out/` und schreibt nach stdout. Die Umleitung gehört auf den
Host: `EvalAnalysis/` liegt ausserhalb von `src/backend/` und ist deshalb nicht
in den Container gemountet.

## Warum die Zahlen hier stehen und nicht der Pfad

`src/backend/eval/out/` ist gitignored und rein lokal. Ein Verweis auf
`2026-09-10T14-06-47Z` ist auf jedem anderen Rechner tot, deshalb trägt der
Bericht Modell, Rate, wirksame Schwellen und Git-SHA im Volltext.

## Was ein Bericht nicht kann

Die Refusal-Rate misst, ob die Pipeline unterdrückt hat — nicht, ob die
Antwort inhaltlich richtig war. Ein Modell, das in Prosa korrekt verweigert
(«steht nicht im Kontext»), ohne das WEISS_NICHT-Protokoll zu bedienen, zählt
als Fehler. Der Abschnitt «Abweichungen im Wortlaut» liefert deshalb jede
abweichende Antwort im Volltext; die Einordnung macht ein Mensch und schreibt
sie in die Befunde-Datei.
