# -*- coding: utf-8 -*-
"""Risiko-Deckungs-Punkt je Profil, und was unsere Halluzinationsrate NICHT zaehlt.

Drei Groessen, die extern vergleichbar sind:
  1. Verweigerung durch das Modell allein (Stufe 2a) -- vergleichbar mit der
     "negative rejection rate" der RAG-Benchmarks, die rohes Modellverhalten messen.
  2. Was die nachgelagerten Stufen zusaetzlich beitragen.
  3. Eine strenge Halluzinationsrate ueber ALLE ausgelieferten Antworten, auch die
     zu out_of_corpus-Fragen -- die zaehlt eval/test_in_corpus_quality.py nicht mit.
"""
import csv
import json

import yaml
from eval.gold_dataset import _corpus_dir

RUNS = {
    "openai": ("2026-09-16T04-52-06Z", "2026-09-16T04-50-07Z"),
    "qwen3-local": ("2026-09-16T05-00-52Z", "2026-09-16T04-52-42Z"),
    "gpt-oss-local": ("2026-09-16T05-19-11Z", "2026-09-16T05-03-00Z"),
    "ministral3-local": ("2026-09-16T13-27-52Z", "2026-09-16T12-48-47Z"),
    "gemma4-local": ("2026-09-16T15-28-34Z", "2026-09-16T13-32-22Z"),
}
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
meta = yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))
G = {q["id"]: q for q in meta["questions"]}
labels = {}
with open("/tmp/labels-R04.csv", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        labels[(row["profil"], row["frage"])] = row

WRONG = {"F1", "F2", "S3"}

print("1) Out-of-Corpus-Verweigerung: Modell allein gegen ganze Pipeline (alle 22 Fragen)")
print("Profil            | nur Modell | Pipeline | Beitrag der Stufen 2b/3")
for prof, (ooc, _) in RUNS.items():
    entries = json.load(open(f"eval/out/{prof}/{ooc}/details.json"))
    n = len(entries)
    model_only = sum(1 for e in entries if e["response"].get("suppression_reason") == "generation_refused")
    pipeline = sum(1 for e in entries if e["response"]["suppressed"])
    print(f"{prof:17s} |   {model_only/n:5.1%}   |  {pipeline/n:5.1%}  |  +{(pipeline-model_only)/n:4.1%}")

print()
print("2) Risiko-Deckung (Entwicklungs-Set, 58 Fragen, Einordnung aus labels/R04.csv)")
print("Profil            | ausgeliefert | davon inhaltlich falsch | strenge Fehlerrate")
for prof, (ooc, ic) in RUNS.items():
    delivered, wrong = 0, []
    for path in (f"eval/out/{prof}/{ooc}", f"eval/out/{prof}/in-corpus/{ic}"):
        for e in json.load(open(path + "/details.json")):
            if e["id"] in HOLDOUT or e["response"]["suppressed"]:
                continue
            delivered += 1
            row = labels.get((prof, e["id"]))
            if row and (row["klasse"] in WRONG or row["nebenklasse"] in WRONG):
                wrong.append(e["id"])
    rate = len(wrong) / delivered if delivered else 0.0
    print(f"{prof:17s} |      {delivered:2d}      |            {len(wrong)}            |      {rate:5.1%}   {wrong}")

print()
print("3) Was die offizielle Halluzinationsrate ausschliesst")
print("   Pool laut eval/test_in_corpus_quality.py: in_corpus + bewertete adversarial.")
for prof, (ooc, ic) in RUNS.items():
    ooc_delivered = [
        e["id"]
        for e in json.load(open(f"eval/out/{prof}/{ooc}/details.json"))
        if not e["response"]["suppressed"]
    ]
    wrong = [
        q for q in ooc_delivered
        if (labels.get((prof, q)) or {}).get("klasse") in WRONG
    ]
    print(f"{prof:17s} | ausgelieferte Out-of-Corpus-Antworten: {len(ooc_delivered)} "
          f"| davon inhaltlich falsch: {len(wrong)} {wrong}")
