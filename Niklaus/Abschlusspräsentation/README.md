# Abschlusspräsentation — Arbeitsordner Niklaus

Alles zu **Block 2 (Technischer Aufbau)** und **Block 5 (Fazit & Ausblick)**. Retos
Gesamtgliederung liegt weiterhin unter
[`Artefakten/Abschlusspräsentation/`](../../Artefakten/Abschlusspräsentation/Inhalte_Abschlusspräsentation.md).

## Was wo liegt

| Ordner / Datei | Inhalt |
|---|---|
| `build/build_block2.py` · `build/build_block5.py` | **erzeugen die alten Decks neu.** Lesen die Vorlage aus `Archive/` und schreiben auch wieder dorthin |
| `Archive/` | Stand vom 19.09.2026: beide Decks, die **Notizen**, die Vorlage, ein Zwischenstand und das Detail-Backup |
| `Archive/Block2_Notizen.md` · `Archive/Block5_Notizen.md` | **die wichtigste Arbeitsgrundlage**: Sprechtext je Folie, Antworten auf Nachfragen, Belege mit Fundstelle, offene Entscheide |
| `Pipeline-Trace/` | Rohdaten und Auswertungen zum Beispiel Q1/Q2 plus `wortsuche_bilanz.py` |
| `Archive/assets/` | Lara-Portrait (aus Christophs Assets) |

**Vorlage nicht löschen:** `Archive/Block2_Technischer-Aufbau.html` ist die erste, knappe Fassung
von Block 2. Beide Build-Skripte holen daraus CSS, Foliennavigation und vier Folien
(Architektur, Lara fragt zweimal, Eval-Gerüst, Gold muss Gold sein).

## Neu bauen

```bash
python Niklaus/Abschlusspräsentation/build/build_block2.py
python Niklaus/Abschlusspräsentation/build/build_block5.py
```

Die Skripte sind selbstgenügsam (nur Standardbibliothek) und überschreiben die beiden HTML-Dateien
**in `Archive/`**. Jede Folie steht als Python-Aufruf `S.append(slide(...))` im Skript — Folien
umbauen, ergänzen oder streichen heisst: diese Aufrufe ändern und neu bauen.

**Dieser Ordner bleibt frei für die neuen Folien.** Neue Decks kommen hierher, mit eigenem
Build-Skript; die Bilder dazu aus `Archive/assets/` kopieren oder von dort referenzieren.

## Stand vom 19.09.2026

- **Block 2:** 19 Folien, rund 10:25. Architektur → Lara fragt zweimal → die richtige Antwort →
  Pipeline-Überblick → Suchen (5 Folien) → Mischen → Vorprüfung (2) → Antworten (2) →
  Nachprüfung (2) → Befunde → Eval → «Gold muss Gold sein».
- **Block 5:** 6 Folien, rund 3:35. Zielwerte sind Hypothesen → die Wortsuche kann schaden →
  hilft oder schadet? Beides → was wir als Nächstes messen würden → lokale Modelle → Schluss.
- **Layout:** übernommen von Christoph (1600×900-Canvas, Story links, Karte rechts,
  Punkt-Navigation, Inter). Q1 trägt überall ein blaues Abzeichen mit §, Q2 ein violettes mit
  Sprechblase.

## Was beim Neustart wiederverwendbar ist

1. **Die Notizen** — dort steht jede Zahl mit Fundstelle. Auch wenn die Folien komplett neu
   entstehen, bleibt das der Inhalt.
2. **Das Beispiel Q1/Q2** (`Pipeline-Trace/`): zwei echte Läufe gegen den Stack, jeder Schritt
   belegt, plus die Erklärung, was daran interessant ist.
3. **Zwei eigene Messungen**, die über das Beispiel hinausgehen:
   - `Pipeline-Trace/wortsuche_bilanz.py` — Wortsuche über 56 Gold-Fragen: 3-mal hilft sie,
     5-mal schadet sie, 48-mal kein Unterschied.
   - der Gold-Defekt `SAMW-OOC-03` (Issue #142): Die Antwort steht im Korpus, das Gold sagt
     «nicht enthalten».
4. **Die Bausteine der Decks** — Balken, Skalen, Zutaten-Tabellen, Chips, Abzeichen: alles im
   CSS-Block der Build-Skripte, mit Klassennamen wie `.fund`, `.bars`, `.chip`, `.qb`.

## Offene Punkte (unverändert)

- **Zeit:** Block 2 braucht rund 10½ Minuten, Retos Gliederung sieht 6–7 vor; Block 5 rund 3½
  statt 1–2. Mit Reto klären.
- **Gold-Folie mit Frank absprechen** (er hat das Dataset abgenommen, T-48).
- **Christoph:** Zwei Ungenauigkeiten auf seiner Learnings-Folie 2 — Details in
  `Archive/Block5_Notizen.md`, «Offene Entscheide».
- **T-62 liegt auf einem Branch** (`feat/T-62-rag-optimierung-r00`), nicht auf `main`.
