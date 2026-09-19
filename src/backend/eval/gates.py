"""Die drei produktiven Reliability-Gates aus ADR-009, an einer Stelle.

Vorher dreifach: `REFUSAL_RATE_GATE` in `eval/test_out_of_corpus_refusal.py` (T-28),
`HALLUCINATION_RATE_GATE`/`FALSE_SUPPRESSION_RATE_GATE` in `eval/test_in_corpus_quality.py`
(T-56), und dieselben zwei Werte noch einmal als eigene Konstanten in
`eval/calibrate_grid.py`/`eval/calibrate_report.py` (T-57, Review-Befund). Eine künftige
Änderung an einer NFA-Zahl hätte sonst nur einen Teil der Stellen getroffen.

Die Test-Module importieren diese Konstanten jetzt unter ihrem bisherigen Namen weiter (kein
Verhaltensunterschied), der Sweep verwendet sie direkt.
"""

REFUSAL_RATE_GATE = 0.90  # ADR-009 / issue #35, DoD Kriterium 4
HALLUCINATION_RATE_GATE = 0.0  # ADR-009 Gruppe A, hartes Gate
FALSE_SUPPRESSION_RATE_GATE = 0.15  # ADR-009 Gruppe A, Startwert
