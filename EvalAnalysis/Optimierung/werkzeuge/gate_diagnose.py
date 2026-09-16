# -*- coding: utf-8 -*-
"""Trennt Stufe 0/1 (Retrieval-Gate) ueberhaupt zwischen beantwortbar und nicht?

Wenn die Retrieval-Konfidenz fuer out_of_corpus-Fragen genauso hoch ist wie fuer
in_corpus-Fragen, traegt das Gate nichts zur Verweigerung bei -- dann haengt alles
am Modell und an Stufe 2/3.
"""
import json
import statistics

import yaml
from eval.gold_dataset import _corpus_dir

meta = yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))
CAT = {q["id"]: q["category"] for q in meta["questions"]}

RUNS = (
    "eval/out/openai/2026-09-16T04-52-06Z",
    "eval/out/openai/in-corpus/2026-09-16T04-50-07Z",
)

by_cat = {}
gate_blocked = {}
for path in RUNS:
    for e in json.load(open(path + "/details.json")):
        cat = CAT[e["id"]]
        st = {s["id"]: s for s in e["response"]["debug"]["stages"]}
        rc = st.get("retrieval_confidence") or {}
        val = rc.get("value")
        if val is not None:
            by_cat.setdefault(cat, []).append(float(val))
        reason = e["response"].get("suppression_reason")
        if reason in ("retrieval_gate", "pre_generation_gate", "retrieval_confidence"):
            gate_blocked[cat] = gate_blocked.get(cat, 0) + 1

print("Retrieval-Konfidenz je Kategorie (Stufe 1, Schwelle 0,4):")
print("Kategorie       |  n | Min  | Median | Max  | unter 0,4")
for cat in ("in_corpus", "adversarial", "out_of_corpus"):
    v = by_cat.get(cat) or []
    if not v:
        continue
    under = sum(1 for x in v if x < 0.4)
    print(f"{cat:15s} | {len(v):2d} | {min(v):.2f} | {statistics.median(v):.2f}   | {max(v):.2f} | {under}")

print("\nVon Stufe 0/1 blockiert:", gate_blocked or "keine Frage")

print("\nTop-1-Aehnlichkeit (Stufe 0, Schwelle 0,35):")
sims = {}
for path in RUNS:
    for e in json.load(open(path + "/details.json")):
        chunks = e["response"]["debug"].get("chunks") or []
        if chunks:
            sims.setdefault(CAT[e["id"]], []).append(max(c.get("score") or 0 for c in chunks))
for cat in ("in_corpus", "adversarial", "out_of_corpus"):
    v = sims.get(cat) or []
    if v:
        print(f"{cat:15s} | n={len(v):2d} | Min {min(v):.2f} | Median {statistics.median(v):.2f} | Max {max(v):.2f}")
