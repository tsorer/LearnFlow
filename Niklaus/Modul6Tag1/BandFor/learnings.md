# Learnings

## Der Generator schreibt ungefragt Tests in den Code

Beobachtung: In der BandFor-Pipeline (Modul 5B) hat der **Generator** nicht nur die
Funktion `band_for` erzeugt, sondern **unaufgefordert gleich pytest-Tests mit in
`code.py`** geschrieben (ein `import pytest` oben, `test_*`-Funktionen unten).

Interessant — aber **nicht das, was wir wollen**: Der Generator soll **reinen Code**
liefern. Validierung und Tests kommen **später** und **getrennt** (eigener Schritt,
eigene Datei, z. B. `test_code.py`).

### Warum das stört

- Implementierung und Tests stecken in **einer** Datei.
- Dadurch hängt das **Produktivmodul zur Import-Zeit von pytest ab**: Ohne
  installiertes pytest lässt sich `band_for` nicht einmal importieren
  (`from code import band_for` scheitert schon an `import pytest`).
- Vermischt zwei Verantwortlichkeiten, die bewusst in getrennten Schritten der
  Pipeline liegen sollen (erst Code, dann prüfen/testen).

### Takeaway

- Den Generator-Prompt so schärfen, dass **nur Code** herauskommt — keine Tests,
  kein `import pytest`, kein `__main__`-Testblock.
- Tests sind ein **eigener Schritt** (Modul 6, `test_code.py`): dort gehören
  Happy Path, Grenzwerte, ungültige Typen und die Fälle, die ein fauler
  Entwickler vergisst (NaN, bool) hin — nicht in die Implementierung.

## Tests gegen die Spec, nicht gegen den Code

**Meine Tests wurden gegen den Code geschrieben, nicht gegen eine unabhängige
Spec.** Genau das wollen wir **nicht**.

Ich habe `code.py` gelesen und die Tests passend zu seinem *tatsächlichen*
Verhalten formuliert. Das ist **zirkulär**: „der Code tut, was der Code tut."
Ein grüner Balken heisst dann nur *in sich konsistent* — nicht *korrekt*.

Konkrete Folge: Solche Tests **zementieren fragwürdiges Verhalten**, statt es
aufzudecken. Beispiele aus `test_code.py`:

- `NaN` → still `"niedrig"` (kein Fehler) — Test grün, weil ich es so behauptet
  habe. Ob das *richtig* ist, sagt der Test nicht.
- `bool` → `True` wird als `1` zu `"hoch"` — genauso gut ein Bug, den der Test
  jetzt festschreibt.

**Was wir wollen:** Der Test wird aus der **Spec** (`spec.md`) abgeleitet, nicht
aus der Implementierung. Dann kann ein Test **rot** werden und eine echte
Abweichung zwischen Soll (Spec) und Ist (Code) sichtbar machen — statt das
Verhalten des Codes bloss zu spiegeln.

**Merksatz:** *Test gegen den Code prüft Konsistenz. Test gegen die Spec prüft
Korrektheit.*
