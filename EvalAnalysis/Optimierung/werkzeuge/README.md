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

Die Lauf-IDs sind in `r00_extract.py` und `r00_runs.py` fest eingetragen. Die Rohdaten unter
`src/backend/eval/out/` sind gitignored und liegen nur auf dem Messrechner.
