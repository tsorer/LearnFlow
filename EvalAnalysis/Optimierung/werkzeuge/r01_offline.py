"""R01 offline: Stufe 2 mit alter und neuer Satzzerlegung auf den gespeicherten R00-Antworten.

Kein LLM, kein Embedding, keine Datenbank: gelesen werden Antworttext, Kontext und
Retrieval-Score aus details.json. Nachgerechnet werden Coverage, Konfidenz, Band und
die Entscheidung bis vor den Self-Check. Wo eine Antwort neu in den Self-Check-Bereich
fällt und es für genau diesen Text kein gespeichertes Urteil gibt: «Self-Check offen».

Voraussetzung: /tmp/confidence_r00.py = confidence.py aus dem R00-Stand (git show).
"""
import collections, importlib.util, json, re, sys

from app.services import confidence as new

spec = importlib.util.spec_from_file_location("confidence_r00", "/tmp/confidence_r00.py")
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)

RUNS = {  # R00
    "openai": ("2026-09-14T21-24-38Z", "2026-09-14T21-22-57Z"),
    "qwen3-local": ("2026-09-14T21-33-46Z", "2026-09-14T21-25-06Z"),
    "gemma4-local": ("2026-09-15T06-03-35Z", "2026-09-15T04-52-33Z"),
    "gpt-oss-local": ("2026-09-14T18-12-16Z", "2026-09-14T18-00-05Z"),
    "ministral3-local": ("2026-09-14T18-45-03Z", "2026-09-14T18-15-48Z"),
}
# Aufruf mit Argument «r01»: statt der R00-Läufe die R01-Live-Läufe nachrechnen (neueste
# vollständige Läufe ab Start der R01-Kette). Isoliert die Wirkung der neuen Satzzerlegung auf
# genau die Antworttexte, die im R01-Lauf entstanden sind.
if "r01" in sys.argv:
    import glob, os
    def _newest(pattern):
        c = [d for d in sorted(glob.glob(pattern)) if os.path.basename(d) >= "2026-09-15T12-13" and os.path.exists(d + "/details.json")]
        return os.path.basename(c[-1]) if c else None
    RUNS = {p: (_newest(f"eval/out/{p}/2*"), _newest(f"eval/out/{p}/in-corpus/2*")) for p in RUNS}
    RUNS = {p: r for p, r in RUNS.items() if all(r)}

MIN_COV, MEDIUM, HIGH, SC_LOW, SC_HIGH = 0.5, 0.45, 0.75, 0.45, 0.75
HOLDOUT = set(json.load(open("/tmp/holdout.json")))

# Einzelne Regeln abschalten, um ihren Beitrag zu messen.
_orig_segments, _orig_pair = new._segments, new._LETTER_PAIR_ABBREVIATION
RULES = {
    "ordinal": lambda on: setattr(new, "_continues_ordinal", new.__dict__["_continues_ordinal_orig"] if on else (lambda a, b: False)),
    "klammer_abk": lambda on: setattr(new, "_LETTER_PAIR_ABBREVIATION", _orig_pair if on else old._LETTER_PAIR_ABBREVIATION),
    "einleitung": lambda on: setattr(new, "_is_lead_in", new.__dict__["_is_lead_in_orig"] if on else (lambda t: False)),
    "kurzer_listenpunkt": lambda on: setattr(new, "_segments", _orig_segments if on else (lambda a: [(s, False) for s, _ in _orig_segments(a)])),
}
new._continues_ordinal_orig, new._is_lead_in_orig = new._continues_ordinal, new._is_lead_in

def set_rules(active):
    for name, toggle in RULES.items():
        toggle(name in active)

def decide(module, entry, sc_verdicts):
    r = entry["response"]
    reason = r.get("suppression_reason")
    if reason in ("retrieval_gate", "retrieval_confidence", "generation_refused", "generation_truncated"):
        return reason, None
    answer = r["debug"]["llm_calls"][0]["response"].strip()
    n_ctx = sum(1 for c in r["debug"]["chunks"] if c.get("in_top_n"))
    cit = module.check_citations(answer, n_ctx)
    if not cit.valid:
        return "citation_invalid", cit.coverage
    if cit.coverage < MIN_COV:
        return "citation_coverage", cit.coverage
    score = round(0.5 * r["confidence"]["retrieval_score"] + 0.5 * cit.coverage, 4)
    if score < MEDIUM:
        return "confidence_band", cit.coverage
    if SC_LOW <= score < SC_HIGH:
        verdict = sc_verdicts.get(answer)
        if verdict is None:
            return "self_check_offen", cit.coverage
        return (None if verdict == "GEDECKT" else "self_check"), cit.coverage
    return None, cit.coverage

report = collections.defaultdict(dict)
variants = {"R00 (alt)": None, "R01 alle Regeln": set(RULES)} | {f"nur {n}": {n} for n in RULES}
changes = []
for prof, (ooc, ic) in RUNS.items():
    entries = []
    for e in json.load(open(f"eval/out/{prof}/{ooc}/details.json")):
        e.setdefault("category", "out_of_corpus"); entries.append(e)
    entries += json.load(open(f"eval/out/{prof}/in-corpus/{ic}/details.json"))
    entries = [e for e in entries if e["id"] not in HOLDOUT]
    sc = {}
    for e in entries:
        st = {s["id"]: s for s in e["response"]["debug"]["stages"]}
        if st.get("self_check", {}).get("ran"):
            sc[e["response"]["debug"]["llm_calls"][0]["response"].strip()] = st["self_check"]["value"]
    # Kontrolle: der Code-Stand des Laufs muss die gespeicherten Entscheide reproduzieren —
    # R00-Läufe mit der alten, R01-Läufe mit der neuen Zerlegung.
    ref = new if "r01" in sys.argv else old
    if ref is new: set_rules(set(RULES))
    mismatch = [e["id"] for e in entries if decide(ref, e, sc)[0] != e["response"].get("suppression_reason")]
    for label, active in variants.items():
        mod = old if active is None else new
        if active is not None: set_rules(active)
        ooc_ok = ooc_n = fs = ic_n = offen = 0
        for e in entries:
            reason, _ = decide(mod, e, sc)
            if e["category"] == "out_of_corpus":
                ooc_n += 1; ooc_ok += reason is not None
            if e["category"] == "in_corpus":
                ic_n += 1; fs += reason is not None and reason != "self_check_offen"; offen += reason == "self_check_offen"
        report[prof][label] = (ooc_ok, ooc_n, fs, ic_n, offen)
    set_rules(set(RULES))
    for e in entries:
        ro, co = decide(old, e, sc); rn, cn = decide(new, e, sc)
        if (ro, co) != (rn, cn):
            changes.append((prof, e["id"], e["category"], ro, co, rn, cn))
    print(f"{prof:17} Kontrolle Lauf reproduziert: {'ja' if not mismatch else 'NEIN ' + str(mismatch)}")

print("\nProfil | Variante | OOC verweigert | False-Suppression (in_corpus) | davon Self-Check offen")
for prof, rows in report.items():
    for label, (a, b, fs, n, offen) in rows.items():
        print(f"{prof:17} | {label:24} | {a}/{b} | {fs}/{n} | {offen}")
print("\nGeänderte Entscheide/Coverage (Dev-Set):")
for c in changes:
    print(" ", c)

# Wie oft der Self-Check laufen müsste (Dev-Set, jede Antwort, die Stufe 2 passiert)
print("\nSelf-Check-Bereich (0,45 ≤ Konfidenz < 0,75) — Antworten, die Stufe 2 passieren:")
for prof, (ooc, ic) in RUNS.items():
    entries = []
    for e in json.load(open(f"eval/out/{prof}/{ooc}/details.json")):
        e.setdefault("category", "out_of_corpus"); entries.append(e)
    entries += json.load(open(f"eval/out/{prof}/in-corpus/{ic}/details.json"))
    counts = {}
    for label, mod in (("R00", old), ("R01", new)):
        band_n = high_n = 0
        for e in entries:
            if e["id"] in HOLDOUT: continue
            r = e["response"]
            if r.get("suppression_reason") in ("retrieval_gate", "retrieval_confidence", "generation_refused", "generation_truncated"): continue
            ans = r["debug"]["llm_calls"][0]["response"].strip()
            n = sum(1 for c in r["debug"]["chunks"] if c.get("in_top_n"))
            cit = mod.check_citations(ans, n)
            if not cit.valid or cit.coverage < MIN_COV: continue
            score = round(0.5 * r["confidence"]["retrieval_score"] + 0.5 * cit.coverage, 4)
            band_n += SC_LOW <= score < SC_HIGH; high_n += score >= SC_HIGH
        counts[label] = (band_n, high_n)
    print(f"  {prof:17} Self-Check läuft: R00 {counts['R00'][0]} → R01 {counts['R01'][0]} | Band hoch (ohne Prüfung): R00 {counts['R00'][1]} → R01 {counts['R01'][1]}")
