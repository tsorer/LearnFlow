# Ü3 – Iterieren & Fehlerbehandlung
**Datum:** 2026-06-24

---

**User:** Erweitere die Umrechnungs-Funktion: behandle auch ungültige Eingaben (null, leere Werte, falsche Typen). Behalte den bestehenden Test und füge Tests für die Fehlerfälle hinzu.

**Claude:** Bestehende Dateien gelesen, dann erweitert:

### temperature.py — Validierung ergänzt

```python
def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert a temperature from Celsius to Fahrenheit.

    Args:
        celsius: Temperature in degrees Celsius. Must be a numeric value (int or float).

    Returns:
        Temperature in degrees Fahrenheit.

    Raises:
        TypeError: If celsius is not a numeric type.
        ValueError: If celsius is None or an empty string.
    """
    if celsius is None:
        raise ValueError("celsius must not be None")
    if not isinstance(celsius, (int, float)):
        raise TypeError(f"celsius must be a number, got {type(celsius).__name__}")
    return celsius * CELSIUS_TO_FAHRENHEIT_FACTOR + FAHRENHEIT_OFFSET
```

### test_temperature.py — 4 neue Fehlerfälle

```python
def test_none_raises_value_error():
    with pytest.raises(ValueError):
        celsius_to_fahrenheit(None)

def test_string_raises_type_error():
    with pytest.raises(TypeError):
        celsius_to_fahrenheit("100")

def test_empty_string_raises_type_error():
    with pytest.raises(TypeError):
        celsius_to_fahrenheit("")

def test_list_raises_type_error():
    with pytest.raises(TypeError):
        celsius_to_fahrenheit([100])
```

### Ergebnis

```
8 passed in 0.04s
```

Alle 4 ursprünglichen Tests unverändert bestanden, 4 neue Fehlertests grün.

---

**User:** exportiere den Chat-Verlauf als Ü3_Iterieren_Git_*

**Claude:** Chatverlauf als `Ü3_Iterieren_Git_2026-06-24.md` gespeichert.
