"""R00: holdout split, per-question outcomes, deviation cases, timing stats."""
import collections, csv, glob, hashlib, json, math, os, statistics
import yaml
from eval.gold_dataset import _corpus_dir

RUNS = {  # fixed: the runs of 2026-09-14 used as baseline
    "openai":           ("2026-09-14T21-24-38Z", "2026-09-14T21-22-57Z"),
    "qwen3-local":      ("2026-09-14T21-33-46Z", "2026-09-14T21-25-06Z"),
    "gemma4-local":     ("2026-09-15T06-03-35Z", "2026-09-15T04-52-33Z"),
    "gpt-oss-local":    ("2026-09-14T18-12-16Z", "2026-09-14T18-00-05Z"),
    "ministral3-local": ("2026-09-14T18-45-03Z", "2026-09-14T18-15-48Z"),
}
OUT = "/tmp/r00"; os.makedirs(OUT, exist_ok=True)
gold = yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))
Q = {q["id"]: q for q in gold["questions"]}

# --- holdout: per (category, corpus) sort by sha256(id), take round(30 %) ---
strata = collections.defaultdict(list)
for q in gold["questions"]:
    strata[(q["category"], q["corpus"])].append(q["id"])
holdout = set()
for key, ids in sorted(strata.items()):
    ids.sort(key=lambda i: hashlib.sha256(i.encode()).hexdigest())
    k = round(len(ids) * 0.3)
    holdout.update(ids[:k])
    print("stratum", key, "n", len(ids), "holdout", k, sorted(ids[:k]))
print("holdout total", len(holdout))
json.dump(sorted(holdout), open(f"{OUT}/holdout.json", "w"), indent=1)

def llm_calls(resp):
    return (resp.get("debug") or {}).get("llm_calls") or []

rows, cases, timing = [], [], {}
for prof, (ooc_run, ic_run) in RUNS.items():
    t_gen, t_sc, tok_c, tok_p, arts = [], [], [], [], 0
    for kind, path in (("ooc", f"eval/out/{prof}/{ooc_run}"), ("ic", f"eval/out/{prof}/in-corpus/{ic_run}")):
        details = json.load(open(f"{path}/details.json"))
        for d in details:
            q = Q[d["id"]]; r = d["response"]; dbg = r.get("debug") or {}
            for i, c in enumerate(d["llm_trace"]):
                (t_gen if i == 0 else t_sc).append(c.get("duration_s") or 0)
                u = c.get("usage") or {}
                tok_c.append((u.get("completion_tokens") or 0, c.get("duration_s") or 0)); tok_p.append(u.get("prompt_tokens") or 0)
                arts += c.get("finish_reason") == "length" or not c.get("response_chars")
            expected_refusal = q.get("expected_refusal", False) if q["category"] != "in_corpus" else False
            if q["category"] == "out_of_corpus": expected_refusal = True
            deviation = bool(r.get("suppressed")) != expected_refusal
            row = dict(profile=prof, id=d["id"], category=q["category"], corpus=q["corpus"],
                       holdout=d["id"] in holdout, expected_refusal=expected_refusal,
                       suppressed=r.get("suppressed"), reason=r.get("suppression_reason"),
                       deviation=deviation)
            rows.append(row)
            if deviation and d["id"] not in holdout:
                exp_pages = set((q.get("expected_source") or {}).get("pages") or [])
                chunks = dbg.get("chunks") or []
                ctx = [c for c in chunks if c.get("in_top_n")]
                calls = llm_calls(r)
                cases.append(dict(
                    row, question=q["question"], reference_answer=q.get("reference_answer"),
                    notes=q.get("notes"), expected_pages=sorted(exp_pages),
                    expected_in_context=any(c.get("page") in exp_pages for c in ctx) if exp_pages else None,
                    context=[f"[{n}] {c.get('filename','')[:20]} S.{c.get('page')}" for n, c in enumerate(ctx, 1)],
                    context_text={n: (c.get("content") or "")[:900] for n, c in enumerate(ctx, 1)},
                    message=r.get("message"),
                    raw=[(c.get("response") or "")[:2500] for c in calls],
                    confidence=r.get("confidence"),
                    self_check=(dbg.get("self_check_ran"), dbg.get("self_check_verdict")),
                    trace_finish=[c.get("finish_reason") for c in d["llm_trace"]]))
    def pct(v, p):
        v = sorted(v); return v[min(len(v) - 1, math.ceil(p * len(v)) - 1)] if v else None
    tps = [c / s for c, s in tok_c if s and c]
    timing[prof] = dict(gen_n=len(t_gen), gen_median=statistics.median(t_gen), gen_p95=pct(t_gen, .95), gen_max=max(t_gen),
                        sc_n=len(t_sc), sc_median=statistics.median(t_sc) if t_sc else None, sc_p95=pct(t_sc, .95), sc_max=max(t_sc) if t_sc else None,
                        total_llm_s=sum(t_gen) + sum(t_sc), prompt_median=statistics.median(tok_p), prompt_max=max(tok_p),
                        completion_max=max(c for c, _ in tok_c), tok_per_s_median=statistics.median(tps) if tps else None, artefacts=arts)

with open(f"{OUT}/outcomes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump(cases, open(f"{OUT}/cases.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(timing, open(f"{OUT}/timing.json", "w"), indent=1)

# summary: metrics all vs dev
def rate(sel, cond):
    sel = list(sel); return (sum(1 for r in sel if cond(r)), len(sel))
for prof in RUNS:
    for scope, filt in (("alle", lambda r: True), ("dev", lambda r: not r["holdout"])):
        pr = [r for r in rows if r["profile"] == prof and filt(r)]
        ooc = rate([r for r in pr if r["category"] == "out_of_corpus"], lambda r: r["suppressed"])
        fs = rate([r for r in pr if r["category"] == "in_corpus"], lambda r: r["suppressed"])
        dev = collections.Counter((r["category"], r["reason"]) for r in pr if r["deviation"])
        print(f"{prof:17} {scope:4} OOC-refusal {ooc[0]}/{ooc[1]}  FS {fs[0]}/{fs[1]}  deviations {dict(dev)}")
print("cases (dev only):", len(cases), collections.Counter((c["profile"]) for c in cases))
print(json.dumps(timing, indent=1))
