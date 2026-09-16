# -*- coding: utf-8 -*-
"""Wäre ein modellspezifischer `min_citation_coverage` nötig — und was kostete er?

Für jedes Profil: die Coverage-Werte der Antworten, die Stufe 2b unterdrückt hat,
getrennt nach der Einordnung aus `labels/R04.csv` (inhaltlich richtig vs. falsch), und
was eine gesenkte Schwelle durchliesse — inklusive der falschen Antworten, die
mitkämen.

Die Lauf-IDs sind fest eingetragen (R04). Voraussetzungen: /tmp/holdout.json,
/tmp/labels-R04.csv.

Aufruf: python schwellen.py
"""
import csv
import json
import os
import sys

RUNS = {
    "openai": ("2026-09-16T04-52-06Z", "2026-09-16T04-50-07Z"),
    "qwen3-local": ("2026-09-16T05-00-52Z", "2026-09-16T04-52-42Z"),
    "gpt-oss-local": ("2026-09-16T05-19-11Z", "2026-09-16T05-03-00Z"),
    "ministral3-local": ("2026-09-16T13-27-52Z", "2026-09-16T12-48-47Z"),
    "gemma4-local": ("2026-09-16T15-28-34Z", "2026-09-16T13-32-22Z"),
}
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
labels = {}
with open("/tmp/labels-R04.csv", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        labels[(row["profil"], row["frage"])] = row

print("Profil            | von Stufe 2b unterdrueckt | Coverage-Werte (r=richtig, f=falsch)")
for prof, (ooc, ic) in RUNS.items():
    vals = []
    for path in (f"eval/out/{prof}/{ooc}", f"eval/out/{prof}/in-corpus/{ic}"):
        if not os.path.exists(path + "/details.json"):
            continue
        for e in json.load(open(path + "/details.json")):
            if e["id"] in HOLDOUT:
                continue
            r = e["response"]
            if r.get("suppression_reason") != "citation_coverage":
                continue
            cov = {s["id"]: s for s in r["debug"]["stages"]}["citation_coverage"]["value"]
            row = labels.get((prof, e["id"]))
            mark = {"richtig": "r", "falsch": "f", "vertretbar": "v"}.get(
                (row or {}).get("urteil", ""), "?"
            )
            vals.append((cov, mark, e["id"]))
    vals.sort(reverse=True)
    shown = " ".join(f"{c:.2f}{m}" for c, m, _ in vals)
    print(f"{prof:17s} | {len(vals):2d} Antworten | {shown}")

print()
print("Was eine gesenkte Schwelle je Profil durchliesse (nur Stufe 2b, Stufe 3 danach unveraendert):")
print("Profil            | Schwelle 0.5 (heute) | 0.4 | 0.3 | 0.25 | davon inhaltlich falsch")
for prof, (ooc, ic) in RUNS.items():
    vals = []
    for path in (f"eval/out/{prof}/{ooc}", f"eval/out/{prof}/in-corpus/{ic}"):
        if not os.path.exists(path + "/details.json"):
            continue
        for e in json.load(open(path + "/details.json")):
            if e["id"] in HOLDOUT:
                continue
            r = e["response"]
            if r.get("suppression_reason") != "citation_coverage":
                continue
            cov = {s["id"]: s for s in r["debug"]["stages"]}["citation_coverage"]["value"]
            row = labels.get((prof, e["id"]))
            vals.append((cov, (row or {}).get("urteil", "?")))
    line = [f"{prof:17s} |          {len(vals):2d}          "]
    for t in (0.4, 0.3, 0.25):
        freed = [v for v in vals if v[0] >= t]
        wrong = sum(1 for v in freed if v[1] == "falsch")
        line.append(f"| {len(freed):2d} ({wrong}f)")
    print(" ".join(line))
