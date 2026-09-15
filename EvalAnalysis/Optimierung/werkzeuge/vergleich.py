"""Zwei Runden Frage für Frage vergleichen (Entwicklungs-Set), mit Ursache jeder Änderung.

Aufruf: python vergleich.py <alt-ab> <alt-bis> <neu-ab> <neu-bis> [Profil ...]
  z. B. R01 → R02a: «2026-09-15T12-13 2026-09-15T17 2026-09-15T19-19 9999 qwen3-local»
Je Profil wird im Zeitfenster der neueste vollständige Lauf genommen.

Ursachen: «Antworttext» (anderer Text — Prompt-Wirkung oder Rauschen), «Coverage» (gleicher
Text, andere Bewertung), «Self-Check» (gleicher Text und Coverage, anderes Urteil).
"""
import collections, glob, json, os, sys

import yaml
from eval.gold_dataset import _corpus_dir

A_FROM, A_TO, B_FROM, B_TO = sys.argv[1:5]
PROFILES = sys.argv[5:] or ["openai", "qwen3-local", "gpt-oss-local", "ministral3-local", "gemma4-local"]
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
gold = {q["id"]: q for q in yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))["questions"]}

def expected_refusal(q):
    return True if q["category"] == "out_of_corpus" else bool(q.get("expected_refusal", False))

def newest(pattern, lo, hi):
    c = [d for d in sorted(glob.glob(pattern)) if lo <= os.path.basename(d) < hi and os.path.exists(d + "/details.json")]
    return c[-1] if c else None

def load(prof, lo, hi):
    ooc, ic = newest(f"eval/out/{prof}/2*", lo, hi), newest(f"eval/out/{prof}/in-corpus/2*", lo, hi)
    if not (ooc and ic):
        return None, None
    out = {}
    for path in (ooc, ic):
        for e in json.load(open(path + "/details.json")):
            out[e["id"]] = e
    return out, f"{os.path.basename(ooc)} / {os.path.basename(ic)}"

def view(e):
    r = e["response"]; st = {s["id"]: s for s in r["debug"]["stages"]}
    calls = r["debug"].get("llm_calls") or []
    cov = st.get("citation_coverage") or {}; sc = st.get("self_check") or {}
    return dict(reason=r.get("suppression_reason"), text=calls[0]["response"].strip() if calls else None,
                cov=cov.get("value") if cov.get("ran") else None, sc=sc.get("value") if sc.get("ran") else None,
                message=r.get("message") or "")

for prof in PROFILES:
    a, la = load(prof, A_FROM, A_TO); b, lb = load(prof, B_FROM, B_TO)
    if a is None or b is None:
        print(f"{prof}: Lauf fehlt"); continue
    same = sum(1 for q in a if view(a[q])["text"] == view(b[q])["text"])
    print(f"\n=== {prof}  alt {la}  neu {lb}  wortgleich {same}/{len(a)}")
    dev = [q for q in a if q not in HOLDOUT]
    for label, d in (("alt", a), ("neu", b)):
        ooc = [q for q in dev if gold[q]["category"] == "out_of_corpus"]
        ic = [q for q in dev if gold[q]["category"] == "in_corpus"]
        devs = sum(bool(d[q]["response"]["suppressed"]) != expected_refusal(gold[q]) for q in dev)
        scn = sum(1 for q in dev if view(d[q])["sc"] is not None)
        print(f"  {label}: OOC verweigert {sum(bool(d[q]['response']['suppressed']) for q in ooc)}/{len(ooc)} | "
              f"False-Suppression {sum(bool(d[q]['response']['suppressed']) for q in ic)}/{len(ic)} | Abweichungen {devs} | Self-Check {scn}")
    causes = collections.Counter()
    for q in dev:
        va, vb = view(a[q]), view(b[q])
        if (va["reason"], va["cov"], va["sc"]) == (vb["reason"], vb["cov"], vb["sc"]):
            continue
        cause = "Antworttext" if va["text"] != vb["text"] else ("Coverage" if va["cov"] != vb["cov"] else "Self-Check")
        causes[cause] += 1
        dev_a = bool(a[q]["response"]["suppressed"]) != expected_refusal(gold[q])
        dev_b = bool(b[q]["response"]["suppressed"]) != expected_refusal(gold[q])
        flag = "behoben" if dev_a and not dev_b else ("NEU" if dev_b and not dev_a else "")
        print(f"  {q:24} {gold[q]['category']:13} {str(va['reason']):18} → {str(vb['reason']):18} cov {va['cov']} → {vb['cov']}  sc {va['sc']} → {vb['sc']}  [{cause}] {flag}")
    print(f"  Ursachen: {dict(causes)}")
