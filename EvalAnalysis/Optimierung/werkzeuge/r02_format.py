"""R02: Belegformat der erzeugten Antworten messen, unabhängig von Unterdrückungen.

Je Profil, Entwicklungs-Set, alle Antworten mit Text (keine WEISS_NICHT-Verweigerung):
- fremdes Format: Antwort enthält 【n】, [na], [n.n], [n(…)] oder [a] — von Stufe 2 nicht erkannt
- unbelegte Aussagen: Anteil zählbarer Segmente ohne gültigen Beleg (mit der Satzzerlegung
  des aktuellen Code-Stands)
- Sammelbeleg: Antwort mit mindestens einem unbelegten Segment, auf das im selben Absatz
  ein belegtes folgt

Aufruf: python r02_format.py <Label> <Zeitstempel-ab> [<Zeitstempel-bis>]
  z. B. «R01 2026-09-15T12-13 2026-09-15T17» — nimmt je Profil den neuesten Lauf im Fenster.
"""
import glob, json, os, re, sys

from app.services.confidence import MIN_SEGMENT_WORDS, _REFERENCE, _is_lead_in, _references, _segments, _word_count

LABEL, SINCE = sys.argv[1], sys.argv[2]
UNTIL = sys.argv[3] if len(sys.argv) > 3 else "9999"
PROFILES = ["openai", "qwen3-local", "gpt-oss-local", "ministral3-local", "gemma4-local"]
HOLDOUT = set(json.load(open("/tmp/holdout.json")))
FOREIGN = re.compile(r"【\s*\d+\s*】|\[\s*\d+\s*[a-z]\s*\]|\[\s*\d+\.\d+[a-z]?\s*\]|\[\s*\d+\s*\([^\]]*\)\s*\]|\[[a-z]\]")

def newest(pattern):
    c = [d for d in sorted(glob.glob(pattern)) if SINCE <= os.path.basename(d) < UNTIL and os.path.exists(d + "/details.json")]
    return c[-1] if c else None

print(f"{LABEL}: Profil | Antworten mit Text | fremdes Format | unbelegte Aussagen | Sammelbeleg | Lauf")
for prof in PROFILES:
    ooc, ic = newest(f"eval/out/{prof}/2*"), newest(f"eval/out/{prof}/in-corpus/2*")
    if not (ooc and ic):
        continue
    entries = json.load(open(ooc + "/details.json")) + json.load(open(ic + "/details.json"))
    n_answers = foreign = collected = seg_total = seg_uncited = 0
    for e in entries:
        if e["id"] in HOLDOUT:
            continue
        calls = e["response"]["debug"].get("llm_calls") or []
        if not calls:
            continue
        raw = calls[0]["response"].strip()
        if not raw or raw.upper().startswith("WEISS_NICHT"):
            continue
        n_ctx = sum(1 for c in e["response"]["debug"]["chunks"] if c.get("in_top_n"))
        n_answers += 1
        foreign += FOREIGN.search(raw) is not None
        has_collected = False
        for paragraph in re.split(r"\n\s*\n", raw):
            marks = []
            for segment, is_list in _segments(paragraph):
                text = _REFERENCE.sub(" ", segment)
                legal = {i for i in _references(segment) if 1 <= i <= n_ctx}
                words = _word_count(text)
                if _is_lead_in(text) and not legal:
                    continue
                if words < MIN_SEGMENT_WORDS and not (is_list and legal and words > 0):
                    continue
                marks.append(bool(legal))
            seg_total += len(marks)
            seg_uncited += marks.count(False)
            if any(not m and any(marks[i + 1:]) for i, m in enumerate(marks)):
                has_collected = True
        collected += has_collected
    print(f"{prof:17} | {n_answers:3} | {foreign:3} ({foreign / n_answers:.0%}) | {seg_uncited}/{seg_total} ({seg_uncited / max(seg_total, 1):.0%}) | {collected:3} ({collected / n_answers:.0%}) | {os.path.basename(ic)}")
