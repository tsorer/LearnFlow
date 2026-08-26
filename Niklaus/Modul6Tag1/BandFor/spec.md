# Spec: band_for

Referenz: ADR-008

---

## 1. Funktionssignatur

```python
def band_for(score: float, medium: float, high: float) -> str
```

---

## 2. Parameter-Semantik

| Parameter | Typ   | Bedeutung |
|-----------|-------|-----------|
| `score`   | float | Konfidenz-Score, nominell im Bereich 0.0–1.0 |
| `medium`  | float | Untere Schwelle — ab hier gilt `'mittel'` |
| `high`    | float | Obere Schwelle — ab hier gilt `'hoch'` |

---

## 3. Rückgabewerte und Bedingungen

| Bedingung                                    | Rückgabe    |
|----------------------------------------------|-------------|
| `score >= high`                              | `'hoch'`    |
| `score >= medium` und `score < high`         | `'mittel'`  |
| `score < medium`                             | `'niedrig'` |

Die Auswertung erfolgt von oben nach unten (first-match).

---

## 4. Randfälle

### 4.1 Score genau auf Grenzwert

- Score **genau auf `high`** (z. B. `score=0.8, medium=0.5, high=0.8`) → `'hoch'`
  Grenzwert gehoert zum **hoeheren** Band (inklusive untere Schranke des Bandes).
- Score **genau auf `medium`** (z. B. `score=0.5, medium=0.5, high=0.8`) → `'mittel'`
  Gleiches Prinzip: Grenzwert gehoert ins hoehere Band.
- Score **knapp unterhalb `medium`** (z. B. `score=0.4999, medium=0.5, high=0.8`) → `'niedrig'`

### 4.2 `medium == high`

Wenn beide Schwellen identisch sind (z. B. `medium=0.6, high=0.6`):
- `score >= 0.6` → `'hoch'` (die `>= high`-Bedingung greift zuerst)
- `score < 0.6`  → `'niedrig'` (das `'mittel'`-Band hat Breite 0 — es ist unerreichbar)

### 4.3 Score ausserhalb [0, 1]

Die Funktion **wirft keine Exception** fuer Werte ausserhalb [0, 1]. Die Vergleichslogik gilt unveraendert:
- `score=1.5, high=0.8` → `'hoch'`
- `score=-0.1, medium=0.5` → `'niedrig'`

Bereichsvalidierung ist Aufgabe des Aufrufers.

### 4.4 `medium > high` (inkonsistente Schwellen)

Kein explizites Fehlerhandling gefordert. Die Funktion wertet die Bedingungen mechanisch aus:
- Jeder Score, der `>= medium` ist, ist zwingend auch `>= high`, daher greift stets `'hoch'` oder `'niedrig'`.
- Das `'mittel'`-Band ist bei `medium > high` unerreichbar.

Aufrufende Schicht traegt Verantwortung fuer konsistente Schwellen.

---

## 5. Unit-Test-Anforderungen

Mindestens die folgenden **5 Testfaelle** muessen abgedeckt sein:

| #  | Beschreibung                          | Eingaben                              | Erwartet    |
|----|---------------------------------------|---------------------------------------|-------------|
| T1 | Klarer `'hoch'`-Fall                  | `score=0.9, medium=0.5, high=0.8`    | `'hoch'`    |
| T2 | Klarer `'mittel'`-Fall                | `score=0.6, medium=0.5, high=0.8`    | `'mittel'`  |
| T3 | Klarer `'niedrig'`-Fall               | `score=0.3, medium=0.5, high=0.8`    | `'niedrig'` |
| T4 | Score **genau auf `high`**            | `score=0.8, medium=0.5, high=0.8`    | `'hoch'`    |
| T5 | Score **genau auf `medium`**          | `score=0.5, medium=0.5, high=0.8`    | `'mittel'`  |
| T6 | `medium == high`, Score auf Schwelle  | `score=0.6, medium=0.6, high=0.6`    | `'hoch'`    |
| T7 | Score knapp unter `medium`            | `score=0.4999, medium=0.5, high=0.8` | `'niedrig'` |

T1–T5 sind Pflicht; T6 und T7 werden empfohlen.

---

## 6. Abhängigkeiten

- **Keine externen Bibliotheken.** Ausschliesslich Python-Standardbibliothek.
- Reine Funktion: keine I/O, keine Seiteneffekte, kein globaler Zustand.
