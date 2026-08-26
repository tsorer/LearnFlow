# Spec: band_for(score, medium, high)

Referenz: ADR-008

---

## Signatur

```
band_for(score: float, medium: float, high: float) -> str
```

---

## Inputs

| Parameter | Typ   | Erlaubter Bereich | Bedeutung                        |
|-----------|-------|-------------------|----------------------------------|
| score     | float | [0.0, 1.0]        | Konfidenz-Score                  |
| medium    | float | [0.0, 1.0]        | untere Schwelle für 'mittel'     |
| high      | float | [0.0, 1.0]        | untere Schwelle für 'hoch'       |

Zusatzbedingung: `medium` muss **strikt kleiner** als `high` sein.

---

## Output

Einer der drei deutschen Strings (genau so geschrieben):

- `'niedrig'`
- `'mittel'`
- `'hoch'`

---

## Klassifikationsregeln

| Bedingung                    | Rückgabe   |
|------------------------------|------------|
| score < medium               | 'niedrig'  |
| medium <= score < high       | 'mittel'   |
| score >= high                | 'hoch'     |

Score **auf** der Schwelle gehört ins **höhere** Band (Schwelle ist inklusive oben).

---

## Validierung — ValueError-Fälle

Bei Verletzung einer der folgenden Bedingungen wird ein `ValueError` mit sinnvoller Meldung ausgelöst. Kein Rückgabewert.

| Verletzung                        | Beispiel                          |
|-----------------------------------|-----------------------------------|
| score ausserhalb [0.0, 1.0]       | score = -0.1 oder score = 1.1     |
| medium ausserhalb [0.0, 1.0]      | medium = -0.1 oder medium = 1.1   |
| high ausserhalb [0.0, 1.0]        | high = 1.5                        |
| medium >= high                    | medium = 0.5, high = 0.5          |
| medium > high (strikt)            | medium = 0.7, high = 0.4          |

---

## Grenzfälle mit konkreten Zahlen

### Normalfall-Grenzen

| score | medium | high | Erwartet  | Begründung                         |
|-------|--------|------|-----------|------------------------------------|
| 0.29  | 0.3    | 0.7  | 'niedrig' | score < medium                     |
| 0.30  | 0.3    | 0.7  | 'mittel'  | score == medium → höheres Band     |
| 0.31  | 0.3    | 0.7  | 'mittel'  | medium < score < high              |
| 0.69  | 0.3    | 0.7  | 'mittel'  | score < high                       |
| 0.70  | 0.3    | 0.7  | 'hoch'    | score == high → höheres Band       |
| 0.71  | 0.3    | 0.7  | 'hoch'    | score > high                       |

### Extremwerte von score

| score | medium | high | Erwartet  | Begründung             |
|-------|--------|------|-----------|------------------------|
| 0.0   | 0.3    | 0.7  | 'niedrig' | kleinstmöglicher Score |
| 1.0   | 0.3    | 0.7  | 'hoch'    | grösstmöglicher Score  |

### medium == high → immer ValueError

| score | medium | high | Erwartet   |
|-------|--------|------|------------|
| 0.5   | 0.5    | 0.5  | ValueError |
| 0.0   | 0.3    | 0.3  | ValueError |

`medium == high` ist immer ungültig, unabhängig vom score.

### Schwellen an den Rändern

| score | medium | high | Erwartet  | Begründung                          |
|-------|--------|------|-----------|-------------------------------------|
| 0.0   | 0.0    | 0.5  | 'mittel'  | score == medium == 0.0 → 'mittel'   |
| 0.5   | 0.0    | 0.5  | 'hoch'    | score == high → 'hoch'              |
| 0.5   | 0.5    | 1.0  | 'mittel'  | score == medium → 'mittel'          |
| 1.0   | 0.5    | 1.0  | 'hoch'    | score == high == 1.0 → 'hoch'       |

### Ungültige score-Werte (ValueError)

| score  | medium | high | Erwartet   |
|--------|--------|------|------------|
| -0.01  | 0.3    | 0.7  | ValueError |
| 1.01   | 0.3    | 0.7  | ValueError |

---

## Nicht spezifiziert / ausserhalb Scope

- Verhalten bei NaN oder Infinity ist undefiniert; solche Eingaben müssen nicht explizit abgefangen werden.
- Typ-Checking (z. B. str statt float) ist optional; die Validierung bezieht sich auf den numerischen Wertebereich.
- Keine externen Abhängigkeiten; reine Python-Standardbibliothek.
