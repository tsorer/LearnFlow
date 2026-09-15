import json, re, collections
from app.services.confidence import _segments, MIN_SEGMENT_WORDS, _REFERENCE, _word_count
cases = json.load(open("/tmp/r00/cases.json", encoding="utf-8"))
ODD = re.compile(r"【\s*\d+\s*】|\[\s*\d+\s*[a-z](?:\]|\s*\])|\[\s*\d+\.\d+[a-z]?\s*\]|\[\s*\d+\s*\(|\[[a-z]\]")
GAP = re.compile(r"nicht (?:ab)?gedeckt|nicht genannt|nicht beschrieben|nicht (?:explizit|direkt)|WEISS_NICHT|keine (?:Informationen|Angaben)", re.I)
for c in cases:
    if c["reason"] != "citation_coverage": continue
    raw = c["raw"][0] if c["raw"] else c["message"]
    segs = _segments(raw); feats = collections.Counter()
    for i, s in enumerate(segs):
        w = _word_count(_REFERENCE.sub(" ", s)); has = bool(_REFERENCE.search(s))
        if w < MIN_SEGMENT_WORDS:
            if has: feats["kurz_mit_beleg_übersprungen"] += 1
            continue
        if has: feats["ok"] += 1; continue
        if ODD.search(s): feats["fremdes_zitatformat"] += 1
        elif GAP.search(s): feats["lücke_benannt"] += 1
        elif s.rstrip().endswith(":"): feats["einleitung_doppelpunkt"] += 1
        elif i + 1 < len(segs) and _word_count(_REFERENCE.sub(" ", segs[i+1])) < MIN_SEGMENT_WORDS and _REFERENCE.search(segs[i+1]): feats["satz_falsch_getrennt"] += 1
        else: feats["ohne_beleg"] += 1
    odd_any = bool(ODD.search(raw))
    print(f"{c['profile']:17} {c['id']:24} cov={c['confidence']['citation_coverage']:<6} fremdformat={odd_any!s:5} {dict(feats)}")
