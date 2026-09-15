import json, sys, re
cases = json.load(open(sys.argv[1], encoding="utf-8"))
want = sys.argv[2]
for c in cases:
    key = c["reason"] or ("delivered-" + c["category"])
    if key != want: continue
    conf = c["confidence"] or {}
    raw0 = c["raw"][0] if c["raw"] else c["message"]
    print(f"### {c['profile']} · {c['id']} ({c['category']}) cov={conf.get('citation_coverage')} band={conf.get('band')} sc={c['self_check']} exp_in_ctx={c['expected_in_context']} finish={c['trace_finish']}")
    print("Q:", c["question"])
    if c["reference_answer"]: print("REF:", re.sub(r"\s+", " ", c["reference_answer"])[:300])
    print("ANS:", (raw0 or "").replace("\n", " ⏎ ")[:1100])
    if len(c["raw"]) > 1: print("SC:", c["raw"][1].replace("\n", " ⏎ ")[:400])
    print()
