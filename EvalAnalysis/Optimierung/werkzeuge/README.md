# Werkzeuge

Auswertungsskripte der Runden, damit jede Zahl in den Runden-Dokumenten nachgerechnet
werden kann. Sie laufen im `api`-Container, weil dort `eval/out/` und die Pipeline-Module
liegen — und damit dieselbe Python-Version wie die Pipeline gilt.

Reihenfolge für R00 (aus `src/`):

```bash
W=../EvalAnalysis/Optimierung/werkzeuge
for f in r00_extract r00_runs r00_kennzahlen r00_coverage_zerlegung r00_faelle_anzeigen; do
  docker cp $W/$f.py src-api-1:/tmp/$f.py
done
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r00_extract.py      # Holdout, Fälle, Laufzeiten -> /tmp/r00/
docker exec -w /app src-api-1 python /tmp/r00_runs.py                            # Kennzahlen je Lauf -> /tmp/r00/runs.json
docker cp ../EvalAnalysis/Optimierung/labels/R00.csv src-api-1:/tmp/r00/labels.csv
docker exec -w /app src-api-1 python /tmp/r00_kennzahlen.py                      # -> /tmp/r00/kennzahlen.csv
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r00_coverage_zerlegung.py   # Ursachen der Coverage-Fälle
docker exec src-api-1 python /tmp/r00_faelle_anzeigen.py /tmp/r00/cases.json citation_coverage
```

Den generierten Bericht mit den Einschätzungen je abweichender Antwort erzeugen:

```bash
docker cp ../EvalAnalysis/Optimierung/labels/R00.csv src-api-1:/tmp/labels-R00.csv
docker cp ../EvalAnalysis/Optimierung/holdout.json src-api-1:/tmp/holdout.json
docker exec -w /app src-api-1 python -m eval.compare \
  --einschaetzung /tmp/labels-R00.csv --holdout /tmp/holdout.json \
  > ../EvalAnalysis/Optimierung/berichte/R00_Modellvergleich.md
```

`eval.compare` nimmt je Profil den **neuesten** Lauf — der Bericht ist nur dann der
R00-Bericht, wenn keine neueren Läufe unter `eval/out/` liegen.

R01 (Aufruf analog, zusätzlich `/tmp/confidence_r00.py` = `git show 0dedbaa~1:src/backend/app/services/confidence.py`):

```bash
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r01_offline.py       # A: R00-Antworten alt vs. neu
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r01_offline.py r01   # C: R01-Antworten alt vs. neu
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r01_segmente.py      # Segmentvergleich geänderter Antworten
docker exec -w /app src-api-1 python /tmp/r01_vergleich.py                         # B: live gegen R00, mit Ursache
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/kennzahlen_runde.py R01 2026-09-15T12-13 2026-09-15T17  # Zeilen für kennzahlen.csv
```

R02 (Zeitfenster statt fester Lauf-IDs):

```bash
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r02_format.py R02a 2026-09-15T19-19        # Belegformat der Antworten
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r02b_offline.py R02a 2026-09-15T19-19      # tolerantes Lesen offline
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/vergleich.py 2026-09-15T12-13 2026-09-15T17 2026-09-15T19-19 9999  # R01 → R02a je Frage
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/kennzahlen_runde.py R02a 2026-09-15T19-19   # Zeilen für kennzahlen.csv
```

R03/R04 (Prämissen, Entscheidungsregel):

```bash
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/r03_praemissen.py   2026-09-15T21-36 2026-09-16T04 2026-09-16T04-50 9999            # Annahme-Fragen, zwei Runden
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/abweichungen.py   2026-09-16T04-50 9999                                            # alle Abweichungen mit Antworttext
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/laenge.py   2026-09-15T21-36 2026-09-16T04 2026-09-16T04-50 9999             # Antwortlänge und Belegdichte
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/self_check_statistik.py   2026-09-16T04-50 9999                                            # Stufe 3: Aufrufe und Urteile
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/kennzahlen_runde.py R04 2026-09-16T04-50
docker cp ../EvalAnalysis/Optimierung/labels/R04.csv src-api-1:/tmp/labels-R04.csv
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/schwellen.py   # braucht min_citation_coverage einen Wert je Modell?
```

`schwellen.py` hat keine Zeitfenster-Argumente: die R04-Lauf-IDs stehen fest im Skript, weil
es die Zahlen zu einem bestimmten Abschnitt in `Stellschrauben.md` belegt.

`r03_praemissen.py`, `vergleich.py`, `r02_format.py`, `laenge.py`, `self_check_statistik.py`
und `abweichungen.py` nehmen die Profile als zusätzliche Argumente. Nötig für
`gemma4-local`, das in R02a/R03 pausiert war und deshalb ein anderes Vergleichsfenster
braucht (R01 statt R03).

Pipeline-Review (`Pipeline-Review.md`) — die drei Auswertungen, die nicht an einer Runde
hängen, sondern an der Pipeline selbst. Retrieval ist deterministisch und läuft vor dem
Modell, deshalb genügt je ein Lauf:

```bash
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/retrieval_diagnose.py  # Rang- oder Findungsproblem?
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/recall_at_n.py         # was ein groesseres Kontextfenster braechte
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/gate_diagnose.py       # trennt Stufe 0/1 ueberhaupt?
docker exec -w /app -e PYTHONPATH=/app src-api-1 python /tmp/risiko_deckung.py      # strenge Fehlerrate, Modell- vs. Pipeline-Verweigerung
```

Die Lauf-IDs sind in `r00_extract.py` und `r00_runs.py` fest eingetragen. Die Rohdaten unter
`src/backend/eval/out/` sind gitignored und liegen nur auf dem Messrechner.
