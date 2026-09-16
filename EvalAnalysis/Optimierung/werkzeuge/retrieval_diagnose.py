# -*- coding: utf-8 -*-
"""Ist die Retrieval-Luecke ein Ranking- oder ein Findungsproblem?

Recall auf dem Kontext (top-n) gegen Recall auf der ganzen Kandidatenliste (top-k).
Steht die erwartete Seite in den Kandidaten, aber nicht im Kontext, hilft ein
Re-Ranker. Steht sie gar nicht drin, hilft nur Chunking/Embedding/Query.

Retrieval ist vor dem Modell und deterministisch -- ein Profil genuegt.
"""
import json
import sys

import yaml
from eval.gold_dataset import _corpus_dir

RUN_IC = sys.argv[1] if len(sys.argv) > 1 else "eval/out/openai/in-corpus/2026-09-16T04-50-07Z"
meta = yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))
gold = meta["questions"]
filenames = {key: c["filename"] for key, c in meta["corpora"].items()}

G = {q["id"]: q for q in gold}


def hit(chunk, fn, pages):
    return chunk.get("filename") == fn and chunk.get("page") in pages


rows = []
for e in json.load(open(RUN_IC + "/details.json")):
    q = G[e["id"]]
    src = q.get("expected_source") or {}
    pages = tuple(src.get("pages") or ())
    fn = filenames.get(q.get("corpus"))
    if not pages or not fn:
        continue
    chunks = e["response"]["debug"].get("chunks") or []
    ctx = [c for c in chunks if c.get("in_top_n")]
    r_ctx = len({c["page"] for c in ctx if hit(c, fn, pages)}) / len(pages)
    r_all = len({c["page"] for c in chunks if hit(c, fn, pages)}) / len(pages)
    mrr = 0.0
    for rank, c in enumerate(chunks, 1):
        if hit(c, fn, pages):
            mrr = 1.0 / rank
            break
    rows.append((e["id"], q["category"], r_ctx, r_all, mrr, len(ctx), len(chunks)))

n = len(rows)
print(f"Fragen mit Quellenangabe: {n}   (Lauf {RUN_IC.split('/')[-1]})")
print(f"Recall im Kontext (top-n):      {sum(r[2] for r in rows) / n:.3f}")
print(f"Recall in den Kandidaten (top-k): {sum(r[3] for r in rows) / n:.3f}")
print(f"MRR ueber die Kandidaten:        {sum(r[4] for r in rows) / n:.3f}")
print()
voll_ctx = sum(1 for r in rows if r[2] == 1.0)
voll_all = sum(1 for r in rows if r[3] == 1.0)
gar_nicht = [r for r in rows if r[3] == 0.0]
rang = [r for r in rows if r[3] > r[2]]
print(f"erwartete Seite(n) vollstaendig im Kontext:      {voll_ctx:2d} von {n}")
print(f"erwartete Seite(n) vollstaendig in Kandidaten:   {voll_all:2d} von {n}")
print(f"RANGPROBLEM  (in Kandidaten, nicht im Kontext):  {len(rang):2d}  -> Hebel: Re-Ranking")
print(f"FINDUNGSPROBLEM (gar nicht in top-k gefunden):   {len(gar_nicht):2d}  -> Hebel: Chunking/Embedding/Query")
print()
print("Rangprobleme:", ", ".join(f"{r[0]} ({r[2]:.2f}->{r[3]:.2f})" for r in rang) or "keine")
print("Findungsprobleme:", ", ".join(r[0] for r in gar_nicht) or "keine")
