**Bericht: band_for — Spec vs. Code**

Alle Grenzfälle wurden einzeln durchgerechnet:

- Normalfall-Grenzen (0.29/0.30/0.31/0.69/0.70/0.71 bei medium=0.3, high=0.7): alle korrekt
- Extremwerte score=0.0 → 'niedrig', score=1.0 → 'hoch': korrekt
- medium==high (0.5/0.5/0.5 und 0.3/0.3): beide ValueError ✓
- Randlagen (medium=0.0: score==medium→'mittel'; high=0.5: score==high→'hoch'; medium=0.5,high=1.0: score==medium→'mittel'; score==high==1.0→'hoch'): alle korrekt
- Ungültige score-Werte (-0.01, 1.01): ValueError ✓
- Ungültige medium/high-Werte (-0.1, 1.1, 1.5) und medium>high (0.7>0.4): ValueError ✓
- Signatur exakt wie Spec, nur Standardbibliothek, 16 pytest-kompatible Testfunktionen vorhanden

**URTEIL: PASS**
(report.md wurde nicht geschrieben — Urteil kommt aus der Konsole)

*** ERGEBNIS: PASS in Runde 1 ***