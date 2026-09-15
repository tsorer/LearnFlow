"""R01: Segment-Vergleich alt/neu für jede Antwort, deren Entscheid oder Band sich ändert."""
import importlib.util, json
from app.services import confidence as new
spec = importlib.util.spec_from_file_location("confidence_r00", "/tmp/confidence_r00.py")
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
RUNS = {"openai": ("2026-09-14T21-24-38Z", "2026-09-14T21-22-57Z"), "qwen3-local": ("2026-09-14T21-33-46Z", "2026-09-14T21-25-06Z"), "gemma4-local": ("2026-09-15T06-03-35Z", "2026-09-15T04-52-33Z"), "gpt-oss-local": ("2026-09-14T18-12-16Z", "2026-09-14T18-00-05Z"), "ministral3-local": ("2026-09-14T18-45-03Z", "2026-09-14T18-15-48Z")}
HOLDOUT = set(json.load(open("/tmp/holdout.json")))

def segs(module, answer, n):
    out = []
    raw = module._segments(answer)
    for item in raw:
        s, is_list = (item if isinstance(item, tuple) else (item, False))
        text = module._REFERENCE.sub(" ", s)
        legal = {i for i in module._references(s) if 1 <= i <= n}
        words = module._word_count(text)
        if module is new and new._is_lead_in(text) and not legal: tag = "skip(einleitung)"
        elif words < module.MIN_SEGMENT_WORDS and not (module is new and is_list and legal and words > 0): tag = "skip"
        else: tag = "OK  " if legal else "MISS"
        out.append((tag, s.strip()[:95]))
    return out

def band(score): return "hoch" if score >= 0.75 else "mittel" if score >= 0.45 else "niedrig"

for prof, (o, i) in RUNS.items():
    entries = []
    for e in json.load(open(f"eval/out/{prof}/{o}/details.json")):
        e.setdefault("category", "out_of_corpus"); entries.append(e)
    entries += json.load(open(f"eval/out/{prof}/in-corpus/{i}/details.json"))
    for e in entries:
        if e["id"] in HOLDOUT: continue
        r = e["response"]
        if r.get("suppression_reason") in ("retrieval_gate", "retrieval_confidence", "generation_refused", "generation_truncated"): continue
        ans = r["debug"]["llm_calls"][0]["response"].strip()
        n = sum(1 for c in r["debug"]["chunks"] if c.get("in_top_n"))
        co, cn = old.check_citations(ans, n).coverage, new.check_citations(ans, n).coverage
        rs = r["confidence"]["retrieval_score"]
        so, sn = round(.5 * rs + .5 * co, 4), round(.5 * rs + .5 * cn, 4)
        crossed = (co < 0.5 <= cn) or (band(so) != band(sn))
        if not crossed: continue
        print(f"\n##### {prof} · {e['id']} ({e['category']}) coverage {co}→{cn}, Konfidenz {so} ({band(so)}) → {sn} ({band(sn)}), R00-Entscheid: {r.get('suppression_reason')}")
        for (to, so_), (tn, sn_) in zip(segs(old, ans, n), segs(new, ans, n)) if len(segs(old, ans, n)) == len(segs(new, ans, n)) else []:
            mark = "  " if to == tn else "->"
            print(f"  {mark} {to} | {tn} | {sn_}")
        if len(segs(old, ans, n)) != len(segs(new, ans, n)):
            print("  ALT:"); [print("     ", t, s) for t, s in segs(old, ans, n)]
            print("  NEU:"); [print("     ", t, s) for t, s in segs(new, ans, n)]
