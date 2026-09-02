# Attention: Query, Key und Value

**Vortragsskript** zu den Folien «Ist ein Quadrat auch ein Rechteck?»
10 Folien · 5–10 Minuten · Datei: `attention_qkv_m6t1.html`

---

## Zeitplan

| Folie | Thema | 10 Min | 5 Min |
|---|---|---|---|
| 01 | Die Frage | 0:30 | 0:20 |
| 02 | Q, K, V — drei Rollen | 1:00 | 0:50 |
| 03 | Der Satz und seine Zahlen | 1:15 | 1:00 |
| 04 | Kopf A rechnen | 1:30 | 1:15 |
| 05 | Der Mischschritt | 1:00 | *überspringen* |
| 06 | Kopf B | 0:30 | 0:15 |
| 07 | Kopf C | 0:40 | 0:20 |
| 08 | Zusammenführen → «Ja» | 1:30 | 1:00 |
| 09 | Die Probe | 0:45 | 0:30 |
| 10 | Was das Modell verschweigt | 0:50 | 0:30 |
| | **Summe** | **9:30** | **5:00** |

**Kurzfassung:** Folie 05 ganz auslassen, Folie 06 nur zeigen und «spiegelbildlich» sagen, Folie 10 auf die zwei wichtigsten Punkte kürzen.

---

## Skript

### Folie 01 — Die Frage

> Ich erkläre Attention heute nicht an einem Sprachbeispiel, sondern an einer Frage, bei der wir alle die richtige Antwort kennen: **Ist ein Quadrat auch ein Rechteck?**
>
> Der Vorteil: wir können am Schluss überprüfen, ob die Maschinerie das Richtige herausbekommt. Und wir sehen die Eigenschaft, an der alles hängt — schaut auf die Häkchen an den Seiten. Beim Rechteck sind zwei Paare gleich lang, beim Quadrat alle vier.

**Übergang:** Um dahin zu kommen, brauchen wir drei Begriffe.

---

### Folie 02 — Q, K, V

> Query, Key und Value sind keine drei verschiedenen Dinge. Es sind **drei Rollen desselben Tokens**, erzeugt durch drei trainierte Matrizen aus einem einzigen Embedding.
>
> Die **Query** ist die Frage: Was suche ich? Der **Key** ist die Auffindbarkeit: Wofür werde ich wahrgenommen? Der **Value** ist der Beitrag: Was gebe ich weiter, wenn man mich auswählt?
>
> Der wichtigste Punkt auf dieser Folie: **Key und Value gehören demselben Token, bedeuten aber Verschiedenes.** Wie in einer Suchmaschine — das Stichwort, unter dem ein Dokument gefunden wird, ist nicht der Inhalt des Dokuments.

**Übergang:** Schauen wir uns an, wie das für unseren Satz konkret aussieht.

---

### Folie 03 — Der Satz und seine Zahlen

> Der Satz hat sieben Tokens. Zwei davon sind unsere Formen, vier sind Funktionswörter, und das Fragezeichen ist das siebte.
>
> Zwei Dinge dazu. Erstens: **«ein» kommt zweimal vor und zählt zweimal.** Attention läuft über Positionen, nicht über Vokabeleinträge — jedes Vorkommen ist ein eigenes Token.
>
> Zweitens: **das Fragezeichen ist ein vollwertiges Token.** Es trägt den Satztyp, und dafür bekommt der Vektorraum eine vierte Dimension.
>
> Jetzt legen wir zwei Räume fest. Im **Value-Raum** steht, was ein Token einbringt: das Quadrat ist rechtwinklig, hat vier Seiten und alle Seiten gleich lang — also eins, eins, eins, null. Das Rechteck dasselbe, nur ohne die dritte Eigenschaft. Im **Key-Raum** steht, wonach man ein Token finden kann: geometrische Form, Position früh, Position spät, Satzzeichen.
>
> Diese Tabellen sind von Hand gewählt, damit man die Zahlen lesen kann. Im echten Modell fallen sie aus trainierten Matrizen heraus, und ihre Dimensionen bedeuten nichts, was man benennen könnte.

**Wichtig zu sagen:** Diese beiden Tabellen gelten **immer**, nicht nur an einer bestimmten Stelle. K und V gehören dem Token, nicht dem Frager. Nur die Query wechselt.

**Übergang:** Und jetzt stellen wir vom Fragezeichen aus drei Fragen an diesen Satz.

---

### Folie 04 — Kopf A

> Kopf A fragt: **Wer ist das Subjekt?** Seine Query sucht eine geometrische Form, die früh im Satz steht.
>
> Wir multiplizieren diese Query mit jedem Key. Das Quadrat kommt auf 4, das Rechteck auf 2, alle anderen auf 0. Dann kommt der Softmax: e hoch vier ist 54.6, e hoch zwei ist 7.39, e hoch null ist 1 — und zwar fünfmal, für vier Funktionswörter und das Fragezeichen. Summe 66.99.
>
> Daraus werden die Gewichte: **das Quadrat bekommt 82 Prozent, das Rechteck 11, der Rest je anderthalb.**
>
> Zwei Beobachtungen. Aus einem Score-Abstand von 2 wird ein Verhältnis von 7 zu 1 — **Softmax ist exponentiell, Attention ist bewusst spitz.** Aber: sie schliesst nie jemanden aus. Kein Token bekommt exakt null. Es wird also nie ausgewählt, sondern immer gemischt.

**Übergang:** Wie diese Mischung genau zustande kommt, schauen wir uns einmal in Zeitlupe an.

---

### Folie 05 — Der Mischschritt *(in der Kurzfassung überspringen)*

> Zwei Zutaten, zwei Aufgaben: **die Gewichte bestimmen, wie viel von jedem Token durchkommt — die Values bestimmen, was durchkommt.**
>
> Erst wird jeder Value-Vektor mit seinem Gewicht skaliert. Dann werden die sieben Beiträge spaltenweise addiert, Dimension für Dimension.
>
> Bei «rechtwinklig» und «vier Seiten» stapeln sich zwei Beiträge, weil beide Formen diese Eigenschaften haben. Bei «alle Seiten gleich» trägt nur das Quadrat — deshalb steht dort exakt sein Aufmerksamkeitsgewicht.
>
> Heraus kommt der neue Kontextvektor: **0.93, 0.93, 0.82, 0.01.**

**Nebenbemerkung, wenn Zeit ist:** Die vier Funktionswörter tragen nichts bei — nicht weil ihr Gewicht null wäre, sondern weil ihr Value null ist. Ein Token kann Aufmerksamkeit bekommen und trotzdem nichts liefern.

---

### Folie 06 — Kopf B

> Kopf B fragt: **Womit wird verglichen?** Dieselbe Rechnung, aber er sucht die Form, die spät im Satz steht. Die Gewichte kippen spiegelbildlich: jetzt bekommt das Rechteck 82 Prozent.
>
> Ergebnis: **0.93, 0.93, 0.11, 0.01.** Der Unterschied zu Kopf A steckt allein in der dritten Zahl.

---

### Folie 07 — Kopf C

> Kopf C fragt: **Welcher Satztyp?** Er interessiert sich nur für Satzzeichen und landet zu 90 Prozent auf dem Fragezeichen.
>
> Sein Ergebnis ist fast leer bei den Geometrie-Dimensionen und trägt 0.90 in «ist eine Frage». Damit weiss das Modell, dass ein Ja oder Nein verlangt ist und nicht eine Aussage.

**Ehrlich dazusagen:** Im Deutschen markiert eigentlich die Verberststellung die Frage — «Ist ein Quadrat…» ist auch ohne Fragezeichen eine Frage. Wir bündeln beide Signale im Fragezeichen, damit das Beispiel mit einem Träger auskommt.

---

### Folie 08 — Zusammenführen

> Jetzt haben wir drei Ergebnisse — **alle drei am Fragezeichen**, der letzten Position, weil dort die Antwort entsteht. Konkateniert sind das zwölf Zahlen.
>
> Ein Schritt fehlt aber noch: Die zwölf Zahlen laufen zuerst durch die **Output-Projektion W-O**. Das ist der einzige Ort, an dem sich die Köpfe überhaupt vermischen — vorher stehen sie unverbunden nebeneinander. Danach kommen Residual und LayerNorm, und **erst jetzt endet die Attention.**
>
> Das Feedforward-Netz liest zwei Dinge ab. Von Kopf C: Es ist eine Frage, also ist Ja oder Nein gefragt. Von Kopf A und B: Hat das Subjekt mindestens alles, was der Vergleich verlangt?
>
> Rechtwinklig — beide 0.93, erfüllt. Vier Seiten — beide 0.93, erfüllt. Alle Seiten gleich — Subjekt 0.82, Vergleich 0.11. Erfüllt, sogar mehr als nötig.
>
> **Antwort: Ja.** Das Quadrat hat zusätzlich gleich lange Seiten, und Zusatzeigenschaften schaden bei einer Ist-ein-Frage nicht.

**Optional, wenn eine Rückfrage kommt:** Jede der sieben Positionen bekommt so einen Vektor, nicht nur das Fragezeichen. Alle werden gleichzeitig berechnet. Wir schauen nur auf die letzte, weil dort das nächste Token vorhergesagt wird.

---

### Folie 09 — Die Probe

> Machen wir die Gegenprobe: **Ist ein Rechteck auch ein Quadrat?**
>
> Kein gelernter Parameter hat sich geändert — keine Query, keine Matrix, keine Formel. Was sich ändert, ist die Wortstellung, und damit tauschen die Positionsmerkmale zwischen den beiden Formen.
>
> Die ersten beiden Dimensionen sind weiterhin erfüllt. Aber bei «alle Seiten gleich» steht jetzt beim Subjekt 0.11 und beim Vergleich 0.82. **Nicht erfüllt. Antwort: Nein.**
>
> Die ganze Asymmetrie der Frage hängt an einer einzigen Zahl in einer einzigen Dimension — und sie kippt allein durch die Wortstellung.

---

### Folie 10 — Was das Modell verschweigt

> Zum Schluss drei Ehrlichkeiten. *(In der Kurzfassung nur die ersten zwei.)*
>
> **Erstens: Attention beantwortet nichts.** Sie ist Routing, dessen Ziel vom Inhalt abhängt. Sie holt Information an die richtige Position — vergleichen und entscheiden passiert danach.
>
> **Zweitens: Das Weltwissen sitzt hier am falschen Ort.** Dass ein Quadrat gleich lange Seiten hat, steckt real in den FFN-Gewichten. Ich habe es in die Value-Vektoren verschoben, weil die Rechnung sonst unsichtbar bliebe. Beides zugleich gibt es nicht.
>
> **Drittens: Attention-Gewichte sind keine Erklärung.** Dass ein Kopf zu 82 Prozent auf «Quadrat» schaut, heisst nicht, dass die Antwort deswegen zustande kam. Und die schöne Ordnung «ein Kopf, eine Aufgabe» ist in echten Modellen die Ausnahme — viele Köpfe lassen sich ersatzlos entfernen.
>
> Die vollständige Formel steht unten: ein Kopf ist Softmax von Q mal K transponiert, geteilt durch Wurzel d-k, mal V. Und Multi-Head ist die Konkatenation aller Köpfe, multipliziert mit W-O.

**Schlusssatz:** Wenn Sie eines mitnehmen: Key und Value sind zwei verschiedene Dinge. Alles andere folgt daraus.

---

## Zahlen-Spickzettel

**Value-Raum** `[rechtwinklig, vier Seiten, alle Seiten gleich, ist eine Frage]`

| Token | V |
|---|---|
| Quadrat | `[1, 1, 1, 0]` |
| Rechteck | `[1, 1, 0, 0]` |
| ? | `[0, 0, 0, 1]` |
| Funktionswörter | `[0, 0, 0, 0]` |

**Key-Raum** `[geom. Form, steht früh, steht spät, ist Satzzeichen]`

| Token | K |
|---|---|
| Quadrat | `[2, 1, 0, 0]` |
| Rechteck | `[2, 0, 1, 0]` |
| ? | `[0, 0, 0, 2]` |
| Funktionswörter | `[0, 0, 0, 0]` |

**Die drei Queries** — alle am Fragezeichen

| Kopf | Frage | Q | Ergebnis |
|---|---|---|---|
| A | Wer ist das Subjekt? | `[1, 2, 0, 0]` | `[0.93, 0.93, 0.82, 0.01]` |
| B | Womit wird verglichen? | `[1, 0, 2, 0]` | `[0.93, 0.93, 0.11, 0.01]` |
| C | Welcher Satztyp? | `[0, 0, 0, 2]` | `[0.03, 0.03, 0.02, 0.90]` |

**Softmax-Summen:** Kopf A und B je 66.99 · Kopf C 60.60
**Gewichte Kopf A:** Quadrat 0.815 · Rechteck 0.110 · übrige fünf je 0.015

---

## Wenn gefragt wird

**«Warum zählt ‹ein› zweimal?»**
Attention arbeitet über Positionen, nicht über Vokabeleinträge. Jedes Vorkommen hat eigene Q-, K- und V-Vektoren.

**«Hat nicht jeder Kopf eigene Keys und Values?»**
Im Standard-Transformer ja — dort gäbe es 21 Queries, 21 Keys und 21 Values. Wir teilen hier einen K/V-Satz über alle Köpfe. Das ist kein Fehler, sondern **Multi-Query Attention** beziehungsweise GQA, und der Grund dafür ist genau der KV-Cache: weniger K/V-Sätze heisst weniger Speicher.

**«Wo bleibt W-O?»**
Auf Folie 08, zwischen Konkatenation und Feedforward-Netz. Es ist der einzige Ort, an dem die Köpfe sich vermischen.

**«Ist das Fragezeichen wirklich der Satztyp-Träger?»**
Streng genommen nein — im Deutschen macht das die Verberststellung, also «Ist» auf Position 1. Wir bündeln beide Signale im Fragezeichen, um mit einem Träger auszukommen.

**«Woher weiss das Modell, dass ein Quadrat gleich lange Seiten hat?»**
In diesem Beispiel steht es in den Value-Vektoren. Real steht es in den FFN-Gewichten. Ich habe es verschoben, damit die Rechnung sichtbar wird.

**«Warum fehlt die Skalierung durch Wurzel d-k?»**
Weggelassen, damit die Zahlen im Kopf nachvollziehbar bleiben. Real ist sie nötig, sonst sättigt der Softmax bei hohen Dimensionen und die Gradienten verschwinden.

**«Sieht ‹Quadrat› das spätere ‹Rechteck›?»**
Beim Generieren nicht — eine kausale Maske sperrt alles rechts von der eigenen Position. Nur die letzte Position sieht den ganzen Satz, und genau deshalb rechnen wir dort.

**«Ist das eine Schicht oder viele?»**
Eine. Real sind es Dutzende, und der Vergleich wäre über viele davon verteilt.
