"""R02b offline: Stufe 2 liest fremde Referenzformate tolerant — auf gespeicherten Antworten.

Die Variante wird nicht im Quellcode ausprobiert, sondern als Normalisierung vor
`check_citations`: 【1】 → [1], [1a] → [1], [1.2b] → [1], [1(3a)] → [1]. Die Nummer wird wie
bisher gegen 1..n geprüft, eine erfundene Nummer bleibt erfunden. Buchstaben allein ([f])
bleiben keine Referenz.

Aufruf: python r02b_offline.py <Label> <Zeitstempel-ab> [<Zeitstempel-bis>]
"""
import glob, json, os, re, sys

from app.services.confidence import check_citations

LABEL, SINCE = sys.argv[1], sys.argv[2]
UNTIL = sys.argv[3] if len(sys.argv) > 3 else "9999"
PROFILES = ["openai", "qwen3-local", "gpt-oss-local", "ministral3-local", "gemma4-local"]
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
MIN_COV, MEDIUM, SC_LOW, SC_HIGH = 0.5, 0.45, 0.45, 0.75

NORMALIZE = [
    (re.compile(r"【\s*(\d+)\s*】"), r"[\1]"),
    (re.compile(r"\[\s*(\d+)\s*[a-z]\s*\]"), r"[\1]"),
    (re.compile(r"\[\s*(\d+)\.\d+[a-z]?\s*\]"), r"[\1]"),
    (re.compile(r"\[\s*(\d+)\s*\([^\]]*\)\s*\]"), r"[\1]"),
]

def tolerant(text):
    for pattern, repl in NORMALIZE:
        text = pattern.sub(repl, text)
    return text

def newest(pattern):
    c = [d for d in sorted(glob.glob(pattern)) if SINCE <= os.path.basename(d) < UNTIL and os.path.exists(d + "/details.json")]
    return c[-1] if c else None

def decide(e, answer, sc_verdicts):
    r = e["response"]
    if r.get("suppression_reason") in ("retrieval_gate", "retrieval_confidence", "generation_refused", "generation_truncated"):
        return r.get("suppression_reason"), None
    n = sum(1 for c in r["debug"]["chunks"] if c.get("in_top_n"))
    cit = check_citations(answer, n)
    if not cit.valid:
        return "citation_invalid", cit.coverage
    if cit.coverage < MIN_COV:
        return "citation_coverage", cit.coverage
    score = round(0.5 * r["confidence"]["retrieval_score"] + 0.5 * cit.coverage, 4)
    if score < MEDIUM:
        return "confidence_band", cit.coverage
    if SC_LOW <= score < SC_HIGH:
        v = sc_verdicts.get(answer)
        return ("self_check_offen" if v is None else (None if v == "GEDECKT" else "self_check")), cit.coverage
    return None, cit.coverage

print(f"{LABEL}: Profil | Kontrolle | OOC verweigert strikt → tolerant | False-Suppression strikt → tolerant | Self-Check offen | geänderte Antworten")
for prof in PROFILES:
    ooc, ic = newest(f"eval/out/{prof}/2*"), newest(f"eval/out/{prof}/in-corpus/2*")
    if not (ooc and ic):
        continue
    entries = []
    for e in json.load(open(ooc + "/details.json")):
        e.setdefault("category", "out_of_corpus"); entries.append(e)
    entries += json.load(open(ic + "/details.json"))
    entries = [e for e in entries if e["id"] not in HOLDOUT]
    sc = {}
    for e in entries:
        st = {s["id"]: s for s in e["response"]["debug"]["stages"]}
        if st.get("self_check", {}).get("ran"):
            sc[e["response"]["debug"]["llm_calls"][0]["response"].strip()] = st["self_check"]["value"]
    strict_ok = tol_ooc = str_ooc = tol_fs = str_fs = offen = n_ooc = n_ic = 0
    changed, mismatch = [], []
    for e in entries:
        calls = e["response"]["debug"].get("llm_calls") or []
        answer = calls[0]["response"].strip() if calls else ""
        rs, cs = decide(e, answer, sc)
        if rs != e["response"].get("suppression_reason"):
            mismatch.append(e["id"])
        tolerant_answer = tolerant(answer)
        rt, ct = decide(e, tolerant_answer, {**sc, tolerant_answer: sc.get(answer)} if tolerant_answer == answer else sc)
        if e["category"] == "out_of_corpus":
            n_ooc += 1; str_ooc += rs is not None; tol_ooc += rt is not None and rt != "self_check_offen"
        if e["category"] == "in_corpus":
            n_ic += 1; str_fs += rs is not None; tol_fs += rt is not None and rt != "self_check_offen"
        offen += rt == "self_check_offen"
        if (rs, cs) != (rt, ct):
            changed.append(f"{e['id']} ({e['category']}): {rs} {cs} → {rt} {ct}")
    print(f"{prof:17} | {'ja' if not mismatch else 'NEIN ' + str(mismatch)} | {str_ooc}/{n_ooc} → {tol_ooc}/{n_ooc} | {str_fs}/{n_ic} → {tol_fs}/{n_ic} | {offen} | {len(changed)}")
    for c in changed:
        print("     ", c)
