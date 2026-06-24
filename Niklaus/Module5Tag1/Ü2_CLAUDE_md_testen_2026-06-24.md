# Ü2 – CLAUDE.md & Konventionen testen
**Datum:** 2026-06-24

---

**User:** Erstelle eine CLAUDE.md für dieses Übungsprojekt.
Stack: Python.
Konventionen:
- Kommentare auf English
- Funktionen brauchen Doku
- Tests mit (propose tech)
- Klare Namensgebung, keine Magic Numbers

**Claude:** `CLAUDE.md` erstellt mit:
- Stack: Python 3 + pytest
- Docstring-Konvention (Google-Style)
- Teststruktur mit pytest (`test_<module>.py`)
- Naming-Konventionen (`snake_case`, `PascalCase`, `UPPER_SNAKE_CASE`)
- No-Magic-Numbers-Regel mit Beispiel

---

**User:** Erstelle eine Funktion die eine Temperatur von Celsius in Fahrenheit umrechnet, mit einem Test.

**Claude:** `temperature.py` erstellt:
```python
CELSIUS_TO_FAHRENHEIT_FACTOR = 9 / 5
FAHRENHEIT_OFFSET = 32

def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert a temperature from Celsius to Fahrenheit.

    Args:
        celsius: Temperature in degrees Celsius.

    Returns:
        Temperature in degrees Fahrenheit.
    """
    return celsius * CELSIUS_TO_FAHRENHEIT_FACTOR + FAHRENHEIT_OFFSET
```

`test_temperature.py` mit 4 Tests:
- `test_freezing_point` → 0°C = 32.0°F
- `test_boiling_point` → 100°C = 212.0°F
- `test_body_temperature` → 37°C ≈ 98.6°F
- `test_negative_temperature` → -40°C = -40.0°F

---

**User:** (Tests laufen lassen)

**Claude:** pytest war nicht installiert. Installiert via `pip install pytest`.
Alle 4 Tests grün mit `python -m pytest test_temperature.py -v`.

---

**User:** merk dir wie du pytest aufrufen musst unter Win 11

**Claude:** Memory gespeichert: Auf Windows 11 mit venv immer `python -m pytest` verwenden — `pytest` allein wird in PowerShell nicht erkannt (`CommandNotFoundException`).

---

**User:** exportiere diesen Verlauf als Ü2_CLAUDE_md_testen_*

**Claude:** Chatverlauf als `Ü2_CLAUDE_md_testen_2026-06-24.md` gespeichert.
