"""Hilft oder schadet die Wortsuche? Bilanz über das Gold-Dataset.

Vergleicht für jede Gold-Frage mit Seitenanker, welche Antwortseiten im Kontext standen
(heute: Bedeutung + Wörter, gemischt, Top 5) und welche mit der Bedeutungssuche allein im
Kontext gestanden hätten (ihre Top 5). Das Retrieval ist deterministisch und läuft vor dem
Modell, deshalb lässt sich die reine Bedeutungssuche aus den gespeicherten Rängen exakt
nachrechnen — ohne neuen Lauf.

Was das NICHT misst: ob die Antwort mit dem anderen Kontext anders ausgefallen wäre. Dafür
bräuchte es einen echten Lauf mit abgeschalteter Wortsuche.

Aufruf (aus src/backend, lokal — eval/out ist gitignored):
    python ../../Niklaus/Abschlusspräsentation/Pipeline-Trace/wortsuche_bilanz.py [details.json]

Standard: der Lauf, auf den sich EvalAnalysis/Optimierung/Pipeline-Review.md stützt
(Referenzmodell gpt-4o-mini, Runde R04, Korpus SKOS + EU AI Act + SAMW).
"""

import json
import sys
from pathlib import Path

import yaml

RUN = sys.argv[1] if len(sys.argv) > 1 else "eval/out/openai/in-corpus/2026-09-16T04-50-07Z/details.json"
GOLD = Path(__file__).resolve().parents[3] / "LearningCorpus" / "gold-eval-dataset.yaml"

meta = yaml.safe_load(GOLD.read_text(encoding="utf-8"))
questions = {q["id"]: q for q in meta["questions"]}
filenames = {key: c["filename"] for key, c in meta["corpora"].items()}

helped, hurt, same = [], [], []
ctx_total = foreign = foreign_via_words = 0

for entry in json.load(open(RUN, encoding="utf-8")):
    q = questions[entry["id"]]
    chunks = (entry["response"].get("debug") or {}).get("chunks") or []
    if not chunks:
        continue
    fn = filenames.get(q.get("corpus"))
    context = [c for c in chunks if c.get("in_top_n")]

    for c in context:
        ctx_total += 1
        if fn and c["filename"] != fn:
            foreign += 1
            if not 1 <= c["dense_rank"] <= 5:
                foreign_via_words += 1

    pages = set((q.get("expected_source") or {}).get("pages") or [])
    if not pages or not fn:
        continue
    dense_only = [c for c in chunks if 1 <= c["dense_rank"] <= 5]

    def recall(cs):
        return len({c["page"] for c in cs if c["filename"] == fn and c["page"] in pages}) / len(pages)

    today, dense = recall(context), recall(dense_only)
    row = (entry["id"], round(dense, 2), round(today, 2), entry["response"].get("suppression_reason"))
    (helped if today > dense else hurt if today < dense else same).append(row)

n = len(helped) + len(hurt) + len(same)
print(f"Lauf: {RUN}")
print(f"Gold-Fragen mit Seitenanker: {n}")
print(f"Wortsuche hilft:   {len(helped):2}  {helped}")
print(f"Wortsuche schadet: {len(hurt):2}  {hurt}")
print(f"kein Unterschied:  {len(same):2}")
print(f"Recall Antwortseiten — nur Bedeutung: {sum(r[1] for r in helped + hurt + same) / n:.3f}, "
      f"heute gemischt: {sum(r[2] for r in helped + hurt + same) / n:.3f}")
print(f"Kontext-Abschnitte: {ctx_total}, aus fremdem Dokument: {foreign}, "
      f"davon nicht in den Top 5 der Bedeutungssuche: {foreign_via_words}")
