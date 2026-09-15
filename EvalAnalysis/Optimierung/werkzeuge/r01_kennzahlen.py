"""R01: eine Zeile je Profil für kennzahlen.csv (Anhängen an die R00-Zeilen).

Ohne Einordnung der Abweichungen (keine labels/R01.csv): die Spalten dazu bleiben leer.
Voraussetzung: /tmp/holdout.json, /tmp/r00/kennzahlen.csv (Spaltenreihenfolge).
"""
import csv, glob, json, math, os, statistics

import yaml
from eval.gold_dataset import _corpus_dir

SINCE = "2026-09-15T12-13"
PROFILES = ["openai", "qwen3-local", "gemma4-local", "gpt-oss-local", "ministral3-local"]
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
gold = {q["id"]: (True if q["category"] == "out_of_corpus" else bool(q.get("expected_refusal", False)))
        for q in yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))["questions"]}

def newest(pattern):
    c = [d for d in sorted(glob.glob(pattern)) if os.path.basename(d) >= SINCE and os.path.exists(d + "/details.json")]
    return c[-1]

def pct(values, p):
    v = sorted(values)
    return v[min(len(v) - 1, math.ceil(p * len(v)) - 1)] if v else None

fields = next(csv.reader(open("/tmp/r00/kennzahlen.csv", encoding="utf-8")))
rows = []
for prof in PROFILES:
    ooc, ic = newest(f"eval/out/{prof}/2*"), newest(f"eval/out/{prof}/in-corpus/2*")
    ro, ri = json.load(open(ooc + "/run.json")), json.load(open(ic + "/run.json"))
    entries = json.load(open(ooc + "/details.json"))
    for e in entries:
        e.setdefault("category", "out_of_corpus")
    entries += json.load(open(ic + "/details.json"))
    dev = [e for e in entries if e["id"] not in HOLDOUT]
    t_gen, t_sc, tps, arts = [], [], [], 0
    for e in entries:
        for n, c in enumerate(e["llm_trace"]):
            (t_gen if n == 0 else t_sc).append(c["duration_s"])
            comp = (c.get("usage") or {}).get("completion_tokens") or 0
            if comp and c["duration_s"]:
                tps.append(comp / c["duration_s"])
            arts += c["finish_reason"] == "length" or not c["response_chars"]
    ooc_dev = [e for e in dev if e["category"] == "out_of_corpus"]
    ic_dev = [e for e in dev if e["category"] == "in_corpus"]
    row = dict.fromkeys(fields, "")
    row.update(
        runde="R01", profil=prof, modell=ro["model"], git_sha=ri["git_sha"],
        lauf_ooc=os.path.basename(ooc), lauf_ic=os.path.basename(ic),
        ooc_refusal_alle=ro["refusal_rate"], halluzination_alle=ri["hallucination_rate"],
        halluz_pool_alle=ri["hallucination_pool_size"], false_suppression_alle=ri["false_suppression_rate"],
        adversarial_refusal_alle=ri["adversarial_refusal_rate"],
        recall_kontext_alle=ri["retrieval_metrics"]["in_corpus"]["recall_context"],
        dev_fragen=len(dev),
        dev_ooc_refusal=f"{sum(bool(e['response']['suppressed']) for e in ooc_dev)}/{len(ooc_dev)}",
        dev_false_suppression=f"{sum(bool(e['response']['suppressed']) for e in ic_dev)}/{len(ic_dev)}",
        dev_abweichungen=sum(bool(e["response"]["suppressed"]) != gold[e["id"]] for e in dev),
        artefakte=arts, gen_median_s=statistics.median(t_gen), gen_p95_s=pct(t_gen, .95),
        sc_median_s=statistics.median(t_sc) if t_sc else "", sc_p95_s=pct(t_sc, .95) if t_sc else "",
        llm_zeit_total_s=round(sum(t_gen) + sum(t_sc)), tok_s_effektiv_median=round(statistics.median(tps), 1),
    )
    rows.append(row)
    print(row)

with open("/tmp/r00/kennzahlen_r01.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writerows(rows)
