"""R04: Antwortlänge und Belegdichte je Profil in zwei Zeitfenstern (Entwicklungs-Set).

Zeigt, ob eine Prompt-Änderung die Antworten länger macht, ohne dass die Belege
mitwachsen — «Zeichen je Beleg» ist genau die Grösse, die Stufe 2b misst.
Gezählt werden nur Antworten mit Text (keine WEISS_NICHT-Verweigerung).

Aufruf: python laenge.py <alt-ab> <alt-bis> <neu-ab> <neu-bis>
"""
import glob, json, os, re, statistics, sys

A_FROM, A_TO, B_FROM, B_TO = sys.argv[1:5]
PROFILES = ["openai", "qwen3-local", "gpt-oss-local", "ministral3-local", "gemma4-local"]
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
REF = re.compile(r"\[\s*\d+\s*\]")

def newest(pattern, lo, hi):
    c = [d for d in sorted(glob.glob(pattern)) if lo <= os.path.basename(d) < hi and os.path.exists(d + "/details.json")]
    return c[-1] if c else None

def texts(prof, lo, hi):
    ooc, ic = newest(f"eval/out/{prof}/2*", lo, hi), newest(f"eval/out/{prof}/in-corpus/2*", lo, hi)
    if not (ooc and ic):
        return None
    out = []
    for path in (ooc, ic):
        for e in json.load(open(path + "/details.json")):
            if e["id"] in HOLDOUT:
                continue
            calls = e["response"]["debug"].get("llm_calls") or []
            if not calls:
                continue
            raw = (calls[0].get("response") or "").strip()
            if not raw or raw.upper().startswith("WEISS_NICHT"):
                continue
            out.append(raw)
    return out

print("Profil | Antworten | Median Zeichen | Median Belege | Zeichen je Beleg")
for prof in PROFILES:
    row = []
    for lo, hi in ((A_FROM, A_TO), (B_FROM, B_TO)):
        t = texts(prof, lo, hi)
        if t is None or not t:
            row.append(None)
            continue
        chars = statistics.median(len(x) for x in t)
        refs = statistics.median(len(REF.findall(x)) for x in t)
        row.append((len(t), chars, refs, round(sum(len(x) for x in t) / max(1, sum(len(REF.findall(x)) for x in t)))))
    if row[0] and row[1]:
        print(f"{prof:17s} | {row[0][0]:3d} -> {row[1][0]:3d} | {row[0][1]:5.0f} -> {row[1][1]:5.0f} | {row[0][2]:4.0f} -> {row[1][2]:4.0f} | {row[0][3]:4d} -> {row[1][3]:4d}")
    else:
        print(f"{prof:17s} | unvollstaendig")
