"""R01: Live-Lauf gegen R00, Frage für Frage (Entwicklungs-Set), mit Ursache jeder Änderung.

Ursachen: «Antworttext» (Modell hat anders geantwortet — Rauschen, R01 ändert die Generierung
nicht), «Coverage» (gleicher Text, neue Satzzerlegung), «Self-Check» (gleicher Text und
Coverage, anderes Urteil).
"""
import collections, glob, json, os, sys
R00 = {"openai": ("2026-09-14T21-24-38Z", "2026-09-14T21-22-57Z"), "qwen3-local": ("2026-09-14T21-33-46Z", "2026-09-14T21-25-06Z"), "gemma4-local": ("2026-09-15T06-03-35Z", "2026-09-15T04-52-33Z"), "gpt-oss-local": ("2026-09-14T18-12-16Z", "2026-09-14T18-00-05Z"), "ministral3-local": ("2026-09-14T18-45-03Z", "2026-09-14T18-15-48Z")}
SINCE = "2026-09-15T12-13"  # Start der R01-Kette
HOLDOUT = set(json.load(open("/tmp/holdout.json")))

def newest(pattern):
    c = [d for d in sorted(glob.glob(pattern)) if os.path.basename(d) >= SINCE and os.path.exists(d + "/details.json")]
    return c[-1] if c else None

def load(prof, ooc, ic):
    out = {}
    for e in json.load(open(f"{ooc}/details.json")):
        e.setdefault("category", "out_of_corpus"); out[e["id"]] = e
    for e in json.load(open(f"{ic}/details.json")):
        out[e["id"]] = e
    return out

def view(e):
    r = e["response"]; dbg = r["debug"]; st = {s["id"]: s for s in dbg["stages"]}
    calls = dbg.get("llm_calls") or []
    return dict(reason=r.get("suppression_reason"), text=(calls[0]["response"].strip() if calls else None),
                cov=(st.get("citation_coverage") or {}).get("value") if (st.get("citation_coverage") or {}).get("ran") else None,
                sc=(st.get("self_check") or {}).get("value") if (st.get("self_check") or {}).get("ran") else None)

profiles = sys.argv[1:] or list(R00)
for prof in profiles:
    ooc1, ic1 = newest(f"eval/out/{prof}/2*"), newest(f"eval/out/{prof}/in-corpus/2*")
    if not (ooc1 and ic1):
        print(f"{prof}: R01-Lauf noch nicht vollständig"); continue
    a = load(prof, f"eval/out/{prof}/{R00[prof][0]}", f"eval/out/{prof}/in-corpus/{R00[prof][1]}")
    b = load(prof, ooc1, ic1)
    fin = collections.Counter(c["finish_reason"] for e in b.values() for c in e["llm_trace"])
    empty = sum(1 for e in b.values() for c in e["llm_trace"] if not c["response_chars"])
    same_text = sum(1 for q in a if view(a[q])["text"] == view(b[q])["text"])
    print(f"\n=== {prof}  R01-Läufe {os.path.basename(ooc1)} / {os.path.basename(ic1)}  finish={dict(fin)} leer={empty}  wortgleich {same_text}/{len(a)}")
    for scope, keep in (("alle", lambda q: True), ("dev", lambda q: q not in HOLDOUT)):
        def rates(d):
            ooc = [q for q in d if d[q]["category"] == "out_of_corpus" and keep(q)]
            ic = [q for q in d if d[q]["category"] == "in_corpus" and keep(q)]
            return (sum(bool(d[q]["response"]["suppressed"]) for q in ooc), len(ooc), sum(bool(d[q]["response"]["suppressed"]) for q in ic), len(ic),
                    sum(1 for q in d if keep(q) and view(d[q])["sc"] is not None))
        ra, rb = rates(a), rates(b)
        print(f"  {scope:4}: OOC verweigert {ra[0]}/{ra[1]} → {rb[0]}/{rb[1]} | False-Suppression {ra[2]}/{ra[3]} → {rb[2]}/{rb[3]} | Self-Check gelaufen {ra[4]} → {rb[4]}")
    for q in a:
        if q in HOLDOUT: continue
        va, vb = view(a[q]), view(b[q])
        if va["reason"] == vb["reason"] and va["cov"] == vb["cov"] and va["sc"] == vb["sc"]: continue
        cause = "Antworttext" if va["text"] != vb["text"] else ("Coverage" if va["cov"] != vb["cov"] else "Self-Check")
        print(f"  {q:24} {a[q]['category']:13} {str(va['reason']):20} → {str(vb['reason']):20} cov {va['cov']} → {vb['cov']}  sc {va['sc']} → {vb['sc']}  [{cause}]")
