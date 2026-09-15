import csv, json, collections
labels = list(csv.DictReader(open("/tmp/r00/labels.csv", encoding="utf-8")))
outcomes = list(csv.DictReader(open("/tmp/r00/outcomes.csv", encoding="utf-8")))
timing = json.load(open("/tmp/r00/timing.json"))
cases = {(c["profile"], c["id"]) for c in json.load(open("/tmp/r00/cases.json", encoding="utf-8"))}
L = {(l["profil"], l["frage"]): l for l in labels}
print("labels", len(labels), "cases", len(cases), "missing", cases - set(L), "extra", set(L) - cases)
profs = ["openai", "qwen3-local", "gemma4-local", "gpt-oss-local", "ministral3-local"]
RUNS = json.load(open("/tmp/r00/runs.json"))
out = []
for p in profs:
    dev = [o for o in outcomes if o["profile"] == p and o["holdout"] == "False"]
    lab = [l for l in labels if l["profil"] == p]
    cls = collections.Counter(l["klasse"] for l in lab)
    falsch = sum(l["urteil"] == "falsch" for l in lab)
    verstoss = sum(l["protokoll"] == "verstoss" for l in lab)
    pipeline = sum(l["klasse"] in ("S2c", "S2d") for l in lab)
    gold = sum(l["klasse"] == "D" for l in lab)
    ooc = [o for o in dev if o["category"] == "out_of_corpus"]; ic = [o for o in dev if o["category"] == "in_corpus"]
    ooc_ref = sum(o["suppressed"] == "True" for o in ooc); ic_sup = sum(o["suppressed"] == "True" for o in ic)
    ic_pipe = sum(1 for l in lab if l["kategorie"] == "in_corpus" and l["klasse"] in ("S2c", "S2d"))
    t = timing[p]; r = RUNS[p]
    row = dict(runde="R00", profil=p, modell=r["model"], git_sha=r["sha"], lauf_ooc=r["ooc"], lauf_ic=r["ic"],
               ooc_refusal_alle=r["ooc_rate"], halluzination_alle=r["halluz"], halluz_pool_alle=r["pool"], false_suppression_alle=r["fs"],
               adversarial_refusal_alle=r["adv"], recall_kontext_alle=r["recall"],
               dev_fragen=len(dev), dev_ooc_refusal=f"{ooc_ref}/{len(ooc)}", dev_false_suppression=f"{ic_sup}/{len(ic)}",
               dev_abweichungen=len(lab), urteil_falsch=falsch, protokoll_verstoss=verstoss, pipeline_messfehler=pipeline, gold_strittig=gold,
               urteilsfaehigkeit=round(1 - falsch / len(dev), 3), protokolltreue=round(1 - verstoss / len(dev), 3),
               dev_false_suppression_ohne_pipeline=f"{ic_sup - ic_pipe}/{len(ic)}",
               artefakte=t["artefacts"], gen_median_s=t["gen_median"], gen_p95_s=t["gen_p95"], sc_median_s=t["sc_median"], sc_p95_s=t["sc_p95"],
               llm_zeit_total_s=round(t["total_llm_s"]), tok_s_effektiv_median=round(t["tok_per_s_median"], 1),
               klassen=" ".join(f"{k}:{v}" for k, v in sorted(cls.items())))
    out.append(row)
    print(row)
with open("/tmp/r00/kennzahlen.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
