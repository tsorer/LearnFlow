"""Fachliche Konstanten, die mehrere Router teilen (T-63).

Bewusst getrennt von `app/config.py`: das Modul dort baut beim Import die
`Settings` und ruft `validate_secrets()` auf. Was hier steht, ist keine
Betriebseinstellung, sondern eine Festlegung des MVP — sie soll importierbar
sein, ohne dass die Umgebungsvalidierung mitläuft.
"""

# MVP: genau ein hartcodierter Pilot-Bereich (Requirements §3) — User hat noch kein
# eigenes area-Feld. Sobald Bereiche pro User existieren, ersetzt user.area dies hier.
#
# Stand bis T-63 in `app/routers/documents.py` und wurde von `query.py` und
# `quiz.py` von dort importiert — die einzige Router-zu-Router-Kopplung im Backend.
#
# Hierher verschoben, weil die Scalability-NFA den Multi-Bereich-Ausbau „ohne
# Redesign" verlangt: Das ist genau die Konstante, die dieser Ausbau anfasst,
# und sie sollte dann nicht in dem Modul liegen, das zufällig als erstes einen
# Bereich brauchte. `documents.area` trägt den Wert als Spalten-Default
# (`server_default="default"`, Migration 0003) — die beiden gehören zusammen.
PILOT_AREA = "default"
