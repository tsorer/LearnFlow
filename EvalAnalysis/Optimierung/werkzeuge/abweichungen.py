"""Alle Abweichungen einer Runde je Profil auflisten, mit Antworttext zum Einordnen.

Abweichung = die Pipeline hat unterdrückt, obwohl eine Antwort erwartet war, oder
ausgeliefert, obwohl eine Verweigerung erwartet war. Holdout-Fragen bleiben aussen vor.
Grundlage für labels/Rnn.csv — die Einordnung selbst macht ein Mensch.

Aufruf: python abweichungen.py <ab> [<bis>] [Profil ...]
"""
import glob, json, os, sys

import yaml
from eval.gold_dataset import _corpus_dir

SINCE = sys.argv[1]
UNTIL = sys.argv[2] if len(sys.argv) > 2 else "9999"
PROFILES = sys.argv[3:] or ["openai", "qwen3-local", "gpt-oss-local", "ministral3-local", "gemma4-local"]
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
G = {q["id"]: q for q in yaml.safe_load(open(_corpus_dir() / "gold-eval-dataset.yaml", encoding="utf-8"))["questions"]}


def expected_refusal(q):
    return True if q["category"] == "out_of_corpus" else bool(q.get("expected_refusal", False))


def newest(pattern):
    c = [d for d in sorted(glob.glob(pattern)) if SINCE <= os.path.basename(d) < UNTIL and os.path.exists(d + "/details.json")]
    return c[-1] if c else None


for prof in PROFILES:
    ooc, ic = newest(f"eval/out/{prof}/2*"), newest(f"eval/out/{prof}/in-corpus/2*")
    if not (ooc and ic):
        print(f"\n=== {prof}: Lauf fehlt")
        continue
    print(f"\n=== {prof}  {os.path.basename(ooc)} / {os.path.basename(ic)}")
    for path in (ooc, ic):
        for e in json.load(open(path + "/details.json")):
            if e["id"] in HOLDOUT:
                continue
            q = G[e["id"]]
            reason = e["response"].get("suppression_reason")
            exp = expected_refusal(q)
            suppressed = reason is not None
            if suppressed == exp:
                continue
            tr = e["llm_trace"][0]
            calls = e["response"]["debug"].get("llm_calls") or []
            raw = (calls[0].get("response") or "").strip().replace("\n", " ⏎ ") if calls else ""
            st = {s["id"]: s for s in e["response"]["debug"]["stages"]}
            cov = (st.get("citation_coverage") or {}).get("value")
            sc = (st.get("self_check") or {}).get("value")
            print(f"  {e['id']:24s} {q['category']:13s} erwartet={'verweigert' if exp else 'Antwort':10s} "
                  f"ist={reason or 'ausgeliefert':20s} cov={cov} sc={sc} finish={tr['finish_reason']} chars={tr['response_chars']}")
            print(f"     {raw[:500]}")
