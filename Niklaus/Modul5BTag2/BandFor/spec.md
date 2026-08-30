# Spec: band_for(score, medium, high)

Referenz: ADR-008

---

## Funktionssignatur

```
band_for(score: float, medium: float, high: float) -> str
```

Datei: `code.py`

---

## Parameter

| Parameter | Typ   | Bedeutung |
|-----------|-------|-----------|
| `score`   | float | Konfidenz-Score des Systems, erwartet im Bereich 0.0–1.0 |
| `medium`  | float | Untere Schwelle: ab hier gilt ein Score als 'mittel' |
| `high`    | float | Obere Schwelle: ab hier gilt ein Score als 'hoch' |

---

## Rueckgabewerte und Logik

Die Funktion gibt genau einen der drei Strings zurueck.  
Pruefung in dieser Reihenfolge (first-match):

1. `score >= high`   → `'hoch'`
2. `score >= medium` → `'mittel'`
3. sonst             → `'niedrig'`

Ein Score **genau auf einem Schwellenwert gehoert ins hoehere Band**:
- `score == high`   → `'hoch'`
- `score == medium` → `'mittel'`

---

## Preconditions / Validierung

Folgende Bedingungen muessen vor der Berechnung erfuellt sein.  
Sind sie verletzt, wird `ValueError` mit aussagekraeftiger Meldung ausgeloest:

- `0.0 <= medium`
- `medium <= high`
- `high <= 1.0`

Fuer `score` wird **kein** Fehler ausgeloest, wenn er ausserhalb 0.0–1.0 liegt;  
die Bandlogik gilt trotzdem (Verhalten bei Out-of-range-Score ist undefiniert / nicht spezifiziert).

---

## Sonderfall: medium == high

Wenn `medium == high`, gibt es kein 'mittel'-Band.  
Jeder Score unterhalb des gemeinsamen Schwellenwerts faellt direkt in 'niedrig',  
jeder Score ab dem Schwellenwert in 'hoch'.  
(Die Pruef-Reihenfolge stellt das automatisch sicher.)

---

## Erwartete Testfaelle

| # | score | medium | high | Erwartetes Band | Begruendung |
|---|-------|--------|------|-----------------|-------------|
| 1 | 0.9   | 0.4    | 0.7  | `'hoch'`        | score > high |
| 2 | 0.7   | 0.4    | 0.7  | `'hoch'`        | score == high → gehoert ins hoehere Band |
| 3 | 0.5   | 0.4    | 0.7  | `'mittel'`      | medium <= score < high |
| 4 | 0.4   | 0.4    | 0.7  | `'mittel'`      | score == medium → gehoert ins hoehere Band |
| 5 | 0.2   | 0.4    | 0.7  | `'niedrig'`     | score < medium |
| 6 | 0.0   | 0.4    | 0.7  | `'niedrig'`     | Minimum-Score |
| 7 | 1.0   | 0.4    | 0.7  | `'hoch'`        | Maximum-Score |
| 8 | 0.5   | 0.5    | 0.5  | `'hoch'`        | medium == high, score == Schwelle → 'hoch' |
| 9 | 0.4   | 0.5    | 0.5  | `'niedrig'`     | medium == high, score darunter → kein 'mittel' |

---

## Validierungsfaelle (ValueError erwartet)

| medium | high  | Grund |
|--------|-------|-------|
| -0.1   | 0.5   | medium < 0 |
| 0.6    | 0.4   | medium > high |
| 0.3    | 1.1   | high > 1 |
