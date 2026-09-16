"""R03: Fragen mit falscher Annahme und Kontrollfragen, zwei Runden nebeneinander, mit Wortlaut.

Zielfragen (Entwicklungs-Set, adversarial, erwartete Antwort = Richtigstellung):
  AIA-ADV-01, AIA-ADV-02, AIA-ADV-03, SAMW-ADV-01, SAMW-ADV-02, SAMW-ADV-04
Kontrollfragen (sollen verweigert bleiben): SKOS-ADV-02, SKOS-IPV-02 und alle out_of_corpus (Dev).

Aufruf: python r03_praemissen.py <alt-ab> <alt-bis> <neu-ab> <neu-bis>
"""
import glob, json, os, sys

import yaml
from eval.gold_dataset import _corpus_dir

A_FROM, A_TO, B_FROM, B_TO = sys.argv[1:5]
PROFILES = ["openai", "qwen3-local", "gpt-oss-local", "ministral3-local"]
TARGETS = ["AIA-ADV-01", "AIA-ADV-02", "AIA-ADV-03", "SAMW-ADV-01", "SAMW-ADV-02", "SAMW-ADV-04"]
GUARDS = ["SKOS-ADV-02", "SKOS-IPV-02"]
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
G = {q["id"]: q for q in yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))["questions"]}

def newest(pattern, lo, hi):
    c = [d for d in sorted(glob.glob(pattern)) if lo <= os.path.basename(d) < hi and os.path.exists(d + "/details.json")]
    return c[-1] if c else None

def load(prof, lo, hi):
    out = {}
    for p in (newest(f"eval/out/{prof}/2*", lo, hi), newest(f"eval/out/{prof}/in-corpus/2*", lo, hi)):
        if p:
            out.update({e["id"]: e for e in json.load(open(p + "/details.json"))})
    return out

def outcome(e):
    r = e["response"]
    return r.get("suppression_reason") or "ausgeliefert"

ooc_dev = [q for q, v in G.items() if v["category"] == "out_of_corpus" and q not in HOLDOUT]
for prof in PROFILES:
    a, b = load(prof, A_FROM, A_TO), load(prof, B_FROM, B_TO)
    if not b:
        print(f"\n=== {prof}: R03-Lauf fehlt"); continue
    ta = sum(outcome(a[q]) == "ausgeliefert" for q in TARGETS if q in a)
    tb = sum(outcome(b[q]) == "ausgeliefert" for q in TARGETS if q in b)
    oa = sum(outcome(a[q]) != "ausgeliefert" for q in ooc_dev if q in a)
    ob = sum(outcome(b[q]) != "ausgeliefert" for q in ooc_dev if q in b)
    print(f"\n=== {prof}: Annahme-Fragen ausgeliefert {ta}/6 → {tb}/6 | Out-of-Corpus verweigert {oa}/{len(ooc_dev)} → {ob}/{len(ooc_dev)}")
    for q in GUARDS:
        print(f"  Kontrolle {q}: {outcome(a[q])} → {outcome(b[q])}")
    for q in ooc_dev:
        if outcome(a[q]) != outcome(b[q]):
            print(f"  Out-of-Corpus {q}: {outcome(a[q])} → {outcome(b[q])} | {(b[q]['response'].get('message') or '')[:200]!r}")
    for q in TARGETS:
        cov = (b[q]["response"].get("confidence") or {}).get("citation_coverage")
        print(f"  {q}: {outcome(a[q])} → {outcome(b[q])} (Coverage {cov})")
        calls = b[q]["response"]["debug"].get("llm_calls") or []
        if calls:
            print("     R03:", calls[0]["response"].strip().replace("\n", " ⏎ ")[:420])
