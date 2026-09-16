# -*- coding: utf-8 -*-
"""Recall in Abhaengigkeit von context_top_n, plus Redundanz im Kontext.

Beantwortet zwei Fragen aus dem Pipeline-Review:
  1. Wie viel Recall kauft ein groesseres Kontextfenster (ohne Re-Ranker)?
  2. Wie viel des Fensters geht fuer mehrfach dieselbe Seite drauf?
"""
import collections
import json
import statistics
import sys

import yaml
from eval.gold_dataset import _corpus_dir

RUN = sys.argv[1] if len(sys.argv) > 1 else "eval/out/openai/in-corpus/2026-09-16T04-50-07Z"
meta = yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))
filenames = {key: c["filename"] for key, c in meta["corpora"].items()}
G = {q["id"]: q for q in meta["questions"]}


def hit(chunk, fn, pages):
    return chunk.get("filename") == fn and chunk.get("page") in pages


entries = []
for e in json.load(open(RUN + "/details.json")):
    q = G[e["id"]]
    pages = tuple((q.get("expected_source") or {}).get("pages") or ())
    fn = filenames.get(q.get("corpus"))
    if not pages or not fn:
        continue
    chunks = e["response"]["debug"].get("chunks") or []
    entries.append((e["id"], chunks, fn, pages))

print(f"{len(entries)} Fragen mit Quellenangabe\n")
print(" n | Recall | Fragen mit voller Deckung | Prompt-Zeichen (Median)")
for n in (3, 5, 7, 10, 15, 20):
    rec, full, chars = [], 0, []
    for _, chunks, fn, pages in entries:
        cut = chunks[:n]
        r = len({c["page"] for c in cut if hit(c, fn, pages)}) / len(pages)
        rec.append(r)
        full += r == 1.0
        chars.append(sum(len(c.get("content") or "") for c in cut))
    print(f"{n:2d} | {statistics.mean(rec):.3f}  | {full:2d} von {len(entries)}"
          f"                 | {statistics.median(chars):6.0f}")

print("\nRedundanz im heutigen Kontext (die 5 obersten Chunks):")
pages_per_ctx, docs_per_ctx = [], []
for _, chunks, fn, pages in entries:
    cut = chunks[:5]
    pages_per_ctx.append(len({(c.get("filename"), c.get("page")) for c in cut}))
    docs_per_ctx.append(len({c.get("filename") for c in cut}))
print(f"  verschiedene (Datei, Seite) je Kontext: Median {statistics.median(pages_per_ctx):.0f} von 5")
print(f"  Verteilung: {dict(sorted(collections.Counter(pages_per_ctx).items()))}")
print(f"  verschiedene Dokumente je Kontext:      Median {statistics.median(docs_per_ctx):.0f}")
print(f"  Verteilung: {dict(sorted(collections.Counter(docs_per_ctx).items()))}")

print("\nWie viele Seiten erwartet das Gold-Dataset je Frage?")
print(" ", dict(sorted(collections.Counter(len(p) for _, _, _, p in entries).items())))
