# Test-Fixtures (T-12)

Minimale Beispieldokumente für die Parser-Tests — bewusst klein und ohne echte
Inhalte aus dem Fachkorpus.

| Datei | Inhalt |
|---|---|
| `sample.pdf` | 2 Seiten, je 2 Zeilen Text (Helvetica, WinAnsi) — prüft Seitenzuordnung |
| `sample.docx` | 5 Absätze mit `Heading 1` / `Heading 2` — prüft Heading-Erkennung |
| `sample.md` | Überschriften, Absätze und ein Codeblock — prüft, dass `#` im Codeblock kein Heading ist |

`sample.pdf` und `sample.docx` wurden mit einem Wegwerf-Skript aus der Python-
Standardbibliothek erzeugt (PDF von Hand, DOCX als OOXML-ZIP), damit sie
deterministisch und wenige KB gross sind.
