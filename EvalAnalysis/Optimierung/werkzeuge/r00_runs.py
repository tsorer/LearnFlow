import json
RUNS = {"openai": ("2026-09-14T21-24-38Z", "2026-09-14T21-22-57Z"), "qwen3-local": ("2026-09-14T21-33-46Z", "2026-09-14T21-25-06Z"), "gemma4-local": ("2026-09-15T06-03-35Z", "2026-09-15T04-52-33Z"), "gpt-oss-local": ("2026-09-14T18-12-16Z", "2026-09-14T18-00-05Z"), "ministral3-local": ("2026-09-14T18-45-03Z", "2026-09-14T18-15-48Z")}
res = {}
for p, (o, i) in RUNS.items():
    ro = json.load(open(f"eval/out/{p}/{o}/run.json")); ri = json.load(open(f"eval/out/{p}/in-corpus/{i}/run.json"))
    res[p] = dict(model=ro["model"], sha=ri["git_sha"], ooc=o, ic=i, ooc_rate=ro["refusal_rate"], halluz=ri["hallucination_rate"], pool=ri["hallucination_pool_size"], fs=ri["false_suppression_rate"], adv=ri["adversarial_refusal_rate"], recall=ri["retrieval_metrics"]["in_corpus"]["recall_context"])
json.dump(res, open("/tmp/r00/runs.json", "w"), indent=1)
