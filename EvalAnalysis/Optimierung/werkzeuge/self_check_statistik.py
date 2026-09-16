"""R04: Stufe 3 — wie oft ausgeführt, mit welchem Urteil, je Profil (Entwicklungs-Set).

Stufe 3 läuft nur im Konfidenzband 0,45–0,75. Wie oft sie läuft, ist deshalb selbst
ein Befund: sinkt die Coverage, rutschen mehr Antworten ins Band. «nicht auswertbar»
sind Urteile, die weder GEDECKT noch NICHT_GEDECKT sind — sie unterdrücken
fail-closed.

Aufruf: python self_check_statistik.py <ab> <bis> [Profil ...]
"""
import collections, glob, json, os, sys

SINCE, UNTIL = sys.argv[1], sys.argv[2]
PROFILES = sys.argv[3:] or ["openai", "qwen3-local", "gpt-oss-local", "ministral3-local", "gemma4-local"]
HOLDOUT = set(json.load(open("/tmp/holdout.json")))


def newest(pattern):
    c = [d for d in sorted(glob.glob(pattern)) if SINCE <= os.path.basename(d) < UNTIL and os.path.exists(d + "/details.json")]
    return c[-1] if c else None


print("Profil | im Band (Stufe 3 gelaufen) | GEDECKT | NICHT_GEDECKT | nicht auswertbar")
for prof in PROFILES:
    ooc, ic = newest(f"eval/out/{prof}/2*"), newest(f"eval/out/{prof}/in-corpus/2*")
    if not (ooc and ic):
        print(f"{prof}: Lauf fehlt")
        continue
    c = collections.Counter()
    for path in (ooc, ic):
        for e in json.load(open(path + "/details.json")):
            if e["id"] in HOLDOUT:
                continue
            sc = {s["id"]: s for s in e["response"]["debug"]["stages"]}.get("self_check") or {}
            if not sc.get("ran"):
                continue
            c["n"] += 1
            v = sc.get("value")
            c[v if v in ("GEDECKT", "NICHT_GEDECKT") else "andere"] += 1
    print(f"{prof:17s} | {c['n']:3d} | {c['GEDECKT']:3d} | {c['NICHT_GEDECKT']:3d} | {c['andere']:3d}")
