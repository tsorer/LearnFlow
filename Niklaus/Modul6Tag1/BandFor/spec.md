# Spec – band_for(score, medium, high)

Referenz: ADR-008  
Autor: niklaus.luethi@lestra.ch  
Datum: 2026-08-26

---

## Zweck

Ordnet einen Konfidenz-Score einem von drei Bändern zu:
`'hoch'` | `'mittel'` | `'niedrig'`

---

## Signatur

```
band_for(score: float, medium: float, high: float) -> str
```

---

## Parameter

| Parameter | Typ   | Bedeutung                                              |
|-----------|-------|--------------------------------------------------------|
| `score`   | float | Konfidenz-Score des Modells (typisch 0.0 – 1.0)        |
| `medium`  | float | Untere Schwelle: ab hier gilt der Score als 'mittel'   |
| `high`    | float | Obere Schwelle: ab hier gilt der Score als 'hoch'      |

---

## Rückgabewert

| Rückgabe    | Bedeutung                          |
|-------------|------------------------------------|
| `'hoch'`    | score ≥ high                       |
| `'mittel'`  | medium ≤ score < high              |
| `'niedrig'` | score < medium                     |

---

## Klassifikationsregel (Pseudo-Logik)

```
wenn score >= high   → 'hoch'
wenn score >= medium → 'mittel'
sonst               → 'niedrig'
```

---

## Grenzfälle mit konkreten Zahlen

Beispielhafte Schwellen: `medium = 0.5`, `high = 0.8`

| score  | Erwartet    | Begründung                              |
|--------|-------------|-----------------------------------------|
| 1.0    | `'hoch'`    | klar über high                          |
| 0.8    | `'hoch'`    | **exakt auf high** → inklusive Grenze   |
| 0.79   | `'mittel'`  | knapp unter high                        |
| 0.5    | `'mittel'`  | **exakt auf medium** → inklusive Grenze |
| 0.49   | `'niedrig'` | knapp unter medium                      |
| 0.0    | `'niedrig'` | Minimalwert                             |
| -0.1   | `'niedrig'` | score unter 0 → kein Sonderfall         |
| 1.5    | `'hoch'`    | score über 1 → kein Sonderfall          |

---

## Verhalten bei ungültigen Schwellen

### Fall 1 – medium >= high (Schwellen invertiert oder gleich)

Beispiel: `medium = 0.8`, `high = 0.5`

- Die Funktion **wirft einen `ValueError`** mit einer aussagekräftigen Meldung,
  z. B. `"medium muss kleiner als high sein (0.8 >= 0.5)"`.
- **Kein stilles Fallback**, da invertierte Schwellen immer ein Konfigurationsfehler sind.

### Fall 2 – Schwellen sind kein float/int (falscher Typ)

- Die Funktion **wirft einen `TypeError`**.
- Beispiel: `band_for(0.6, "mittel", 0.8)` → TypeError.

### Fall 3 – score ist kein float/int

- Ebenfalls **`TypeError`**.

### Zusammenfassung Fehlerverhalten

| Ungültige Eingabe          | Ausnahme     |
|----------------------------|--------------|
| `medium >= high`           | `ValueError` |
| Schwelle ist kein Zahl-Typ | `TypeError`  |
| score ist kein Zahl-Typ    | `TypeError`  |

---

## Nicht im Scope

- Logging oder Metriken
- Konfiguration aus Dateien/Umgebungsvariablen
- Mehr als drei Bänder
