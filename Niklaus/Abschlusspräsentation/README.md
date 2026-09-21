# Abschlusspräsentation — Arbeitsordner Niklaus

Alles zu **Block 2 (Technischer Aufbau)** und **Block 5 (Fazit & Ausblick)**. Retos
Gesamtgliederung liegt weiterhin unter
[`Artefakten/Abschlusspräsentation/`](../../Artefakten/Abschlusspräsentation/Inhalte_Abschlusspräsentation.md).

## Aktueller Stand

Der Arbeitsordner ist wieder frei für einen neuen Anlauf. Beide bisherigen Fassungen liegen
vollständig und reproduzierbar im Archiv. Teile davon werden wiederverwendet:

| Fassung | Ordner | Block 2 | Block 5 |
|---|---|---|---|
| 19.09.2026 | [`Archive/`](Archive/) | 19 Folien, nur Antwort-Pipeline · `build/build_block2.py` | 6 Folien · `build/build_block5.py` |
| 20.09.2026 | [`Archive/2026-09-20/`](Archive/2026-09-20/) | 17 Folien, rund 9 Min. · `build/build_block2_v3.py` | 5 Folien, rund 4:55 · `build/build_block5_v2.py` |

Alle vier Build-Skripte schreiben in ihren Archivordner zurück; die Ausgabe ist identisch mit
dem archivierten Stand. Die Beschreibung der Fassung vom 20.09. folgt, weil sie die jüngere
Grundlage ist.

## Fassung 20.09. — Block 2

| Datei | Inhalt |
|---|---|
| [`Block2_Technischer-Aufbau.html`](Archive/2026-09-20/Block2_Technischer-Aufbau.html) | **die Folien** — 17 Stück, rund 9 Minuten |
| [`Block2_Notizen.md`](Archive/2026-09-20/Block2_Notizen.md) | Sprechtext je Folie, Belege mit Fundstelle, was bewusst nicht auf den Folien steht, offene Entscheide |
| [`Block2_Themen.md`](Archive/2026-09-20/Block2_Themen.md) | der Themenentscheid davor: welche Themen in den Block gehören und welche nicht |
| [`build/build_block2_v3.py`](build/build_block2_v3.py) | baut die Folien |

**Die Erzählung:** drei Wege durch dasselbe System — Wissen hinein (Parsen, Stückeln,
Einbetten), Frage → Antwort (die Pipeline am Beispiel Q1/Q2), Fragen hinaus (Quiz mit
menschlicher Freigabe) — und zum Schluss die Belege. Roter Faden: *Maschine prüft die Antwort,
Mensch prüft die Frage, Messung prüft beides.* Auf fast jeder Folie steht ein farbiger Kasten
mit «Funktioniert gut», «Funktioniert nicht» oder «Das hat uns überrascht».

## Fassung 20.09. — Block 5

| Datei | Inhalt |
|---|---|
| [`Block5_Fazit-Ausblick.html`](Archive/2026-09-20/Block5_Fazit-Ausblick.html) | **die Folien** — 5 Stück, rund 4:55 |
| [`Block5_Notizen.md`](Archive/2026-09-20/Block5_Notizen.md) | Sprechtext, Belege, bewusste Auslassungen, offene Entscheide |
| [`Block5_Themen.md`](Archive/2026-09-20/Block5_Themen.md) | der Themenentscheid davor |
| [`build/build_block5_v2.py`](build/build_block5_v2.py) | baut die Folien |

**Die Erzählung:** fünf Folien, fünf Fragen — Hält es? · Wo ist noch Luft? · Warum nicht
sofort? · Geht das auch lokal? · Was kommt als Nächstes? Kern ist Folie 3: Bei 80 Testfragen
wiegt jede einzelne mehrere Prozentpunkte, und ein falscher Eintrag im Gold-Dataset bestraft
korrektes Verhalten dauerhaft. Bewusst **nicht** auf den Folien: die strenge Halluzinationsrate
(2,9 %), das Zwischenergebnis des ersten Kalibrierungslaufs und die zwei wirkungslosen
Prüfstufen — alles drei mit vorbereiteter Antwort in den Notizen.

## Begriffe (gilt für beide Blöcke)

Nach dem Begriffs-Review vom 20.09. — ein Wort pro Sache, in beiden Decks gleich:

| Wort | Bedeutung | nicht verwenden für |
|---|---|---|
| **Grenze** | die drei Eval-Ziele: 0 % erfundene Belege · ≥ 90 % Ablehnung · ≤ 15 % fälschlich abgelehnt | Schnittstellen im Dokument, Schwellenwerte |
| **Schwellenwert** (kurz: Schwelle) | die einstellbaren Werte der Pipeline: 0,35 · 0,40 · Belegdeckung · Bandgrenzen | die Eval-Ziele |
| **Prüfung** | wer oder was über Qualität entscheidet (vier Stufen · ein Mensch · die Messung) | — · ersetzt das frühere «Gate» |
| **Kante** | wo ein Dokument geschnitten wird (Überschrift, Absatz, Satz, Seitenwechsel) | — · ersetzt «Schnittgrenze» |
| **Stellschraube** | eine konkrete Einstellung, an der man drehen kann | grosse Massnahmen |
| **Hebel** | eine Verbesserung mit gemessener Wirkung (Re-Ranker, grösseres Testset) | einzelne Einstellungen |
| **Testfragen** | die 80 Fragen des Gold-Datasets | — · «Gold-Dataset» einmal je Block zur Verknüpfung |
| **ablehnen** | die Kennzahl in Block 5 («fälschlich abgelehnt») | in Block 2 heisst die Mechanik weiterhin «unterdrücken» |

## Was wo liegt

| Ordner | Inhalt |
|---|---|
| `Pipeline-Trace/` | **Rohdaten**: zwei echte Läufe (Q1/Q2) mit jeder Zwischenstufe, lesbare Berichte dazu, plus `wortsuche_bilanz.py` (Wortsuche über 56 Gold-Fragen) |
| `Archive/` | Fassung 19.09.2026: Decks, Notizen, die gemeinsame Vorlage (`Block2_Technischer-Aufbau.html`), `assets/` · darin `2026-09-20/`: Fassung 20.09. (Decks, Notizen, Themen) |
| `assets/` | Lara-Portrait (Kopie aus `Archive/assets/` für neue Folien im Arbeitsordner) |
| `build/` | die vier Build-Skripte (je zwei pro Fassung) |

## Belege, auf die sich die Folien stützen

1. **`Pipeline-Trace/`** — jede Zahl des Beispiels, gegen den laufenden Stack erhoben,
   Produktivcode unverändert.
2. **Eigene Messung zur Wortsuche** (`Pipeline-Trace/wortsuche_bilanz.py`): hilft 3×,
   schadet 5×, 48× kein Unterschied.
3. **Gold-Defekt `SAMW-OOC-03`** (Issue #142): Die Antwort steht im Korpus, das Gold sagt
   «nicht enthalten».
4. **Korpuszahlen** direkt aus der Datenbank: 4 Dokumente, 1017 Abschnitte.

## Offene Punkte

- **Zeit:** Block 2 rund 9 Minuten (Plan 6–7), Block 5 rund 5 (Plan 1–2) — zusammen rund sechs
  Minuten über Budget. Kürzungen sind in beiden Notizdateien vorbereitet. Mit Reto klären;
  naheliegendste Quelle ist die Demo.
- **Kommt das Quiz in der Demo vor?** Davon hängt ab, wie ausführlich Weg C sein muss.
- **Gold-Folie mit Frank absprechen** (er hat das Dataset abgenommen, T-48).
- **Abgrenzung zu Christoph** (Wortsuche/T-28) und **zu Frank** (API-First, Security).
- **T-62 liegt auf einem Branch** (`feat/T-62-rag-optimierung-r00`), nicht auf `main`.
