# Ü1 – Setup & Erster Kontakt
**Datum:** 2026-06-24

---

**User:** Erstelle eine kleine Datei mit einer Funktion multiply, die zwei Zahlen multipliziert — in Python

**Claude:** Datei `multiply.py` erstellt:
```python
def multiply(a, b):
    return a * b
```

---

**User:** teste es mit `multiply(3, 4)`

**Claude:** `multiply(3, 4)` gibt `12` zurück — korrekt.

---

**User:** teste es mit `multiply(3, 4)`

**Claude:** `12`

---

**User:** Ja, aber füge auch eine Funktion divide hinzu

**Claude:** `divide` hinzugefügt mit Prüfung auf Division durch null:
```python
def divide(a, b):
    if b == 0:
        raise ValueError("Division durch null ist nicht erlaubt")
    return a / b
```
Test `divide(12, 4)` ergibt `3.0`.

---

**User:** teste es mit `divide(10, 2)`

**Claude:** `divide(10, 2)` ergibt `5.0` — korrekt.

---

**User:** exportiere den Chatverlauf und speicher ihn als Ü1_Setup_Erster_Kontakt_*

**Claude:** Chatverlauf als `Ü1_Setup_Erster_Kontakt_2026-06-24.md` gespeichert.
