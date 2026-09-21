# Abschlusspräsentation — Arbeitsordner Niklaus

Alles zu **Block 2 (Technischer Aufbau)** und **Block 5 (Fazit & Ausblick)**. Retos
Gesamtgliederung liegt weiterhin unter
[`Artefakten/Abschlusspräsentation/`](../../Artefakten/Abschlusspräsentation/Inhalte_Abschlusspräsentation.md).

## Aktueller Stand — gekürzte Fassung (22.09.)

Beide Blöcke sind stark gekürzt und aus den archivierten Fassungen zusammengestellt. Die
Build-Skripte lesen die Archive nur, übernehmen die gewählten Folien und halten jede Änderung
als Korrektur fest, die genau einmal treffen muss. Bilder werden ins HTML eingebettet, jedes
Deck ist also eine einzige Datei. Kopien beider Decks liegen in
[`Artefakten/Abschlusspräsentation/`](../../Artefakten/Abschlusspräsentation/). Nach einem neuen
Build müssen sie von Hand nachgezogen werden.

```bash
docker run --rm -v "$(pwd):/w" -w /w python:3.13-slim python build/build_block2_v4.py
docker run --rm -v "$(pwd):/w" -w /w python:3.13-slim python build/build_block5_v3.py
```

### Block 2 — 6 Folien

[`Block2_Technischer-Aufbau.html`](Block2_Technischer-Aufbau.html) · gebaut von
[`build/build_block2_v4.py`](build/build_block2_v4.py). Die Bereichsleiste hat nur noch drei
Bereiche: Architektur · RAG-Pipeline · Evaluation.

| # | Bereich | Folie | Quelle |
|---|---|---|---|
| 1 | Architektur | Ein Frontend. Zwei Services. Eine Datenbank. | V3 F1 |
| 2 | RAG-Pipeline | Eine Frage. Zwei Formulierungen. (Q1/Q2) | V2 F2 |
| 3 | RAG-Pipeline | Erst suchen, dann antworten, dann prüfen — die fünf Phasen als Flussdiagramm | V2 F4 |
| 4 | RAG-Pipeline | Ist überhaupt etwas Passendes dabei? — Vorprüfung, Schwelle 0,35 | V2 F11 |
| 5 | RAG-Pipeline | Im Zweifel prüft ein zweites Urteil — Self-Check als Flussdiagramm, Pfad von Q2 hervorgehoben | V2 F16 |
| 6 | Evaluation | Wie prüft man, ob die Pipeline gut ist? — drei Schritte, eine Karte je Fragetyp mit Grenze | V2 F18 |

V2 = [`Archive/Block2_Technischer-Aufbau_v2.html`](Archive/Block2_Technischer-Aufbau_v2.html)
(19.09., die letzte Folie ist abgeschnitten archiviert) · V3 =
[`Archive/2026-09-20/Block2_Technischer-Aufbau.html`](Archive/2026-09-20/Block2_Technischer-Aufbau.html).

### Block 5 — 4 Folien

[`Block5_Fazit-Ausblick.html`](Block5_Fazit-Ausblick.html) · gebaut von
[`build/build_block5_v3.py`](build/build_block5_v3.py). Quelle ist die Fassung vom 20.09. (A20).

| # | Folie | Quelle |
|---|---|---|
| 1 | Zwei von drei selbst gesetzten Grenzen sind erreicht | A20 F1 |
| 2 | Bei der dritten Grenze ist noch Luft | A20 F2 |
| 3 | Gold muss Gold sein — grösser werden, zu 100 % stimmen; Bild [`assets/gold.png`](assets/gold.png) | A20 F3 + F5 zusammengelegt |
| 4 | Lokale Modelle: die Qualität ist da — Tabelle mit den drei Grenzen als Spalten (Runde R04) | A20 F4 |

## Archiv

Beide früheren Fassungen liegen vollständig und reproduzierbar im Archiv:

| Fassung | Ordner | Block 2 | Block 5 |
|---|---|---|---|
| 19.09.2026 | [`Archive/`](Archive/) | 19 Folien, nur Antwort-Pipeline · `build/build_block2.py` | 6 Folien · `build/build_block5.py` |
| 20.09.2026 | [`Archive/2026-09-20/`](Archive/2026-09-20/) | 17 Folien, rund 9 Min. · `build/build_block2_v3.py` | 5 Folien, rund 4:55 · `build/build_block5_v2.py` |

Diese vier Build-Skripte schreiben in ihren Archivordner zurück. Die Ausgabe ist inhaltlich
identisch mit dem archivierten Stand, nur die Zeilenenden unterscheiden sich.

## Archiv: Fassung 20.09. — Block 2

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

## Archiv: Fassung 20.09. — Block 5

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
| `assets/` | Lara-Portrait (Block 2 F2) und `gold.png` (Block 5 F3); die Builds betten beide ins HTML ein |
| `build/` | sechs Build-Skripte: je zwei pro archivierter Fassung, dazu `build_block2_v4.py` und `build_block5_v3.py` für den aktuellen Stand |

## Belege, auf die sich die Folien stützen

1. **`Pipeline-Trace/`** — jede Zahl des Beispiels, gegen den laufenden Stack erhoben,
   Produktivcode unverändert.
2. **Eigene Messung zur Wortsuche** (`Pipeline-Trace/wortsuche_bilanz.py`): hilft 3×,
   schadet 5×, 48× kein Unterschied.
3. **Gold-Defekte** (Issue #142, T-65, offen): drei Einträge, deren Erwartung der Korpus nicht
   deckt — `SAMW-OOC-03`, `SKOS-ADV-01`, `SKOS-IPV-02`.
4. **Korpuszahlen** direkt aus der Datenbank: 4 Dokumente, 1017 Abschnitte.
5. **Schwellenwerte** direkt aus der `config`-Tabelle (21.09.): Ähnlichkeit 0,35 · Fundlage 0,40 ·
   Self-Check-Band 0,45–0,75.
6. **Modellvergleich** (Block 5 F4): Runde R04 in `EvalAnalysis/Optimierung/kennzahlen.csv`
   (Branch T-62); erfundene Belege 0 bei allen fünf Modellen.

## Offene Punkte

- **Sprechnotizen zum aktuellen Stand fehlen.** `Block2_Notizen.md` und `Block5_Notizen.md`
  gehören zur Fassung vom 20.09. Stoff für Rückfragen, der bewusst nicht auf den Folien steht:
  - Block 2: Die Vorprüfung hat zwei Stufen (0,35 und 0,40), die Folien zeigen nur die erste.
  - Block 2: Bei 2 der 13 Fangfragen ist «Weiss ich nicht» die erwartete Antwort.
  - Block 2: Die OBV aus dem Beispiel kommt im Gold-Dataset nicht vor.
  - Block 5: «Fälschlich abgelehnt» entsteht in R04 vollständig nach dem Modellaufruf. Das
    Modell lehnt selbst ab, belegt zu wenig oder der Self-Check verneint. Daher die grosse
    Streuung zwischen den Modellen.
  - Block 5: gemma4 hält als einziges Modell das Ausgabeformat zu 100 % ein. Zwei seiner Fehler
    kamen von einem zu tief gesetzten Token-Limit.
- **Zeit neu messen:** Block 2 ist von 17 auf 6 Folien gekürzt, Block 5 von 5 auf 4. Die neue
  Dauer ist noch nicht gemessen.
- **Sichtkontrolle offen:** Block 2 F1, F5 und F6 sowie Block 5 F3 und F4 sind nach den letzten
  Änderungen noch nicht per Screenshot geprüft.
- **Kommt das Quiz in der Demo vor?** In Block 2 kommt das Quiz nicht mehr vor.
- **Gold-Folien mit Frank absprechen** (er hat das Dataset abgenommen, T-48): Block 2 F6 und
  Block 5 F3.
- **Abgrenzung zu Christoph** (Wortsuche/T-28) und **zu Frank** (API-First, Security).
- **T-62 liegt auf einem Branch** (`feat/T-62-rag-optimierung-r00`), nicht auf `main`.
