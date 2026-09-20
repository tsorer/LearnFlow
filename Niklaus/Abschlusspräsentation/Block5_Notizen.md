# Block 5 · Fazit & Ausblick — Notizen

Alles, was **nicht** auf den Folien steht: Sprechtext, Belege mit Fundstelle, Antworten auf
absehbare Nachfragen, bewusste Auslassungen, offene Entscheide.

| | |
|---|---|
| Folien | [`Block5_Fazit-Ausblick.html`](Block5_Fazit-Ausblick.html) — **5 Folien**, rund 4:55 |
| Gebaut von | [`build/build_block5_v2.py`](build/build_block5_v2.py) |
| Sprachliche Leitlinie | **Positiv formulieren und Alltagssprache.** Nicht, was wir nicht gemacht haben, sondern was sich damit machen lässt. Begriffe nach dem Glossar im [README](README.md) |
| Themenentscheid dahinter | [`Block5_Themen.md`](Block5_Themen.md) |
| Baut auf | [`Block2_Notizen.md`](Block2_Notizen.md) — dieselben Grenzen, dasselbe Gold-Dataset |
| Vorherige Fassungen | [`Archive/`](Archive/) (19.09., 6 Folien); die Zwischenstände mit 9 und 8 Folien sind im Build-Skript dokumentiert |

## Die Idee dieses Blocks

**Fünf Folien, fünf Fragen, die das Publikum nach den vorherigen Blöcken wirklich hat:**

| # | Frage | Folie |
|---|---|---|
| 1 | Hält es? | Zwei von drei selbst gesetzten Grenzen sind erreicht |
| 2 | Wo ist noch Luft? | Bei der dritten Grenze — die Schwellenwerte haben wir nie angefasst |
| 3 | Warum dann nicht sofort? | Zuerst muss der Massstab stimmen |
| 4 | Geht das auch lokal? | Die Qualität ist da — es fehlt die Hardware, nicht das Modell |
| 5 | Was kommt als Nächstes? | Gold muss Gold sein · die Auswahl schlägt die Suche — mit dem Schlusssatz |

Der Bogen: Das Versprechen hält → bei der offenen Grenze liegt Potenzial → heben lässt es sich
erst, wenn die Messung feiner wird → Ausblick. Der Satz, der hängen bleiben soll:

> **Der Beleg dafür, dass es hält, ist die eigentliche Arbeit.**

## Ablauf und Zeit

| # | Folie | Abschnitt | Zeit |
|---|---|---|---|
| 1 | Zwei von drei selbst gesetzten Grenzen sind erreicht | Was hält | 0:45 |
| 2 | Bei der dritten Grenze ist noch Luft | gelernt | 1:00 |
| 3 | Zuerst muss der Massstab stimmen | gelernt | 1:10 |
| 4 | Lokale Modelle: die Qualität ist da | Ausblick | 1:00 |
| 5 | Erst der Massstab, dann der grösste Hebel | Ausblick | 1:00 |

**Summe rund 4:55.** Fünf Folien auf fünf Minuten heisst: eine Minute pro Folie, ruhig sprechen.
Wenn es kürzer sein muss: Folie 4 auf die zwei Zeilen Referenz/gemma4 plus einen Satz (−0:30).

---

## Folie für Folie

### 1 · Zwei von drei selbst gesetzten Grenzen sind erreicht

**Überleitung aus Christophs Block:** «Ihr habt gehört, woran wir uns die Zähne ausgebissen
haben. Was davon hält — gemessen?»

**Sagen:** Die drei Grenzen stammen aus unserem eigenen Eval-Entscheid, gesetzt lange vor der
ersten Messung — das ist wichtig für die nächste Folie. Dieselben 80 Fragen wie in Block 2.
Keine erfundene Quelle, in keinem Lauf und bei keinem der fünf Modelle. Fremde Fragen werden in
90,9 % der Fälle abgelehnt. Die dritte Grenze halten wir nicht: 22,2 % statt 15 %.

**Beleg:** `EvalAnalysis/Optimierung/kennzahlen.csv`, Runde R04, Profil `openai`
(`halluzination_alle` 0,0 · `ooc_refusal_alle` 0,9091 · `false_suppression_alle` 0,2222),
Lauf vom 16.09.2026.

**Bewusst nicht auf der Folie — Entscheid vom 20.09.:** die strenge Neuberechnung der
Halluzinationsrate. Der offizielle Pool zählt nur `in_corpus`- und bewertete
`adversarial`-Fragen; ausgelieferte Antworten auf Fragen *ausserhalb* des Korpus fliessen nicht
ein. Streng gerechnet liegt die Referenz bei 2,9 % (1 von 34), und alle fehlerhaften Antworten
stehen genau in der ausgeschlossenen Kategorie (`Pipeline-Review.md` §2a.1, T-62-Branch).

*Falls jemand nachfragt* — ohne Beschönigung: «Die Kennzahl hat einen blinden Fleck:
Ausgelieferte Antworten auf Fragen ausserhalb des Korpus zählen nicht in den Nenner. Streng
gerechnet sind es bei der Referenz knapp drei Prozent, und genau diese Kategorie gehört in die
Kennzahl. Das haben wir selbst gefunden, es steht auf der Liste.» **Nicht** die
Literaturvergleiche (RAGTruth, FACTS Grounding) nennen — unverifiziert.

### 2 · Bei der dritten Grenze ist noch Luft

**Sagen:** Der Wert ist von 31,1 auf 22,2 Prozent gefallen. Gedreht haben wir dabei an zwei
Stellen: wie die Belegprüfung Sätze zerlegt, und am Prompt. An den Schwellenwerten selbst — den
drei Zahlen, ab denen das System schweigt — nie. Die sind Schätzungen vom ersten Tag. Und
inzwischen muss sie niemand mehr schätzen: Ein Lauf rechnet tausende Kombinationen auf
gespeicherten Suchergebnissen durch, ohne Modellaufruf, und schlägt Werte vor.

**Die drei Zahlen auf der Karte:** Ähnlichkeit 0,35 — wie nah ein Abschnitt an der Frage sein
muss. Fundlage 0,40 — wie gut die fünf gefundenen Abschnitte zusammen sein müssen. Belege 0,50 —
wie viele Sätze der Antwort eine gültige Quellennummer tragen müssen. Alle drei stehen seit dem
ersten Tag so in ADR-008.

**Wichtig, damit kein falscher Eindruck entsteht:** Das Eval lief oft — allein für die
Optimierung 23 Messläufe über fünf Modelle. Wer fragt «habt ihr denn nie evaluiert?», bekommt
diese Zahl. Nie geprüft wurde die *Messlatte*, nicht die Pipeline.

**Falls gefragt — was in den Runden geändert wurde:** R01 wie die Belegprüfung Sätze zerlegt
(Ordnungszahlen, Abkürzungen, kurze Listenpunkte). R02 ein Beleg je Aussage im Prompt. R03
verworfen (kein Modell liest eine Ausnahme hinter «antworte ausschliesslich mit WEISS_NICHT»).
R04 zwei Prompt-Regeln zu einer Entscheidung mit drei Fällen zusammengezogen.

**Falls gefragt — wie die Schwellen bisher gesetzt wurden:** von Hand im Admin-Panel. Beim
Eval-Lauf am 09.09. stand die Belegdeckung so auf 0,28 statt 0,50, ohne dass jemand die Zahl
begründen konnte.

**Falls gefragt — was der erste Kalibrierungslauf ergab** (bewusst nicht auf der Folie): «Einen
Vorschlag, der auf den Fragen, mit denen gesucht wurde, beide Grenzen erfüllt — auf den
zurückgehaltenen Fragen aber nicht: 85,7 % statt 90 % Ablehnung. Bei sieben zurückgehaltenen
Fragen ist das eine einzige Frage Unterschied. Deshalb gelten weiter die alten Werte — und
deshalb kommt jetzt Folie 3.»

**Wer es gebaut hat:** Frank (PR #139, gemerged 19.09.). Auf der Folie steht kein Name, es wird
als Teamergebnis erzählt.

**Belege:** `kennzahlen.csv` (R00/R04) · ADR-008 (die drei Schwellenwerte) · ADR-009 (15 % als
Startwert) · `Docs/10_Kalibrierungsbericht.md` · `Pipeline-Trace/Q1.json`, Abschnitt `config`.

### 3 · Zuerst muss der Massstab stimmen

**Die Folie, auf die es ankommt.** Zwei Aussagen, beide konkret:

1. **Jede einzelne Frage wiegt zu viel.** Die 90,9 % von Folie 1 sind 20 von 22 Fragen. Zwei
   Fragen anders beantwortet, und wir liegen unter der Grenze — eine einzige Frage sind
   4,5 Prozentpunkte. Feiner als in solchen Sprüngen lässt sich mit 80 Fragen nicht steuern.
2. **Und wenn eine Frage falsch im Gold steht, ist es fatal.** Dann misst man dauerhaft gegen
   die falsche Erwartung. Der gezeigte Eintrag verlangt «Weiss ich nicht» — die Frist steht aber
   im Leitfaden. Die Pipeline hat richtig geantwortet und wurde dafür als Fehler gezählt.

**Der Eintrag ist `SAMW-OOC-03`** (auf der Folie ohne Kennung, damit niemand mitlesen muss).
Drei solche Fälle haben wir gefunden, dokumentiert in Issue #142: `SAMW-OOC-03`, `SKOS-ADV-01`,
`SKOS-IPV-02`.

**Der Satz, der sitzen soll:** «Nach der Abnahme prüft niemand mehr gegen die Quelle — ein
falscher Eintrag bestraft korrektes Verhalten dauerhaft und unbemerkt.»

**Falls gefragt — was folgt daraus konkret?** Die drei Einträge korrigieren, das Set
vergrössern, die Halluzinations-Kennzahl um die ausgelieferten Fragen ausserhalb des Korpus
erweitern. Steht auf Folie 5, Punkt 1.

**Falls gefragt — habt ihr das Gold selbst gemacht?** Ja, im Team; Frank hat es abgenommen
(T-48). Kein Vorwurf an ihn: Ein Datensatz altert wie Code, und geprüft haben wir ihn erst, als
wir anfingen, gegen ihn zu optimieren.

**Falls gefragt — gilt das auch für eure anderen Zahlen?** Ja, und das ist der Punkt. Auch die
22,2 % von Folie 1 stehen auf demselben Massstab. Dazu kommt: derselbe Lauf an zwei Tagen ergab
26,7 % und 33,3 %; bei Temperatur 0 fielen 15 von 80 Antworten anders aus. Deshalb steht der
Massstab in der Reihenfolge vorn.

**Belege:** `LearningCorpus/gold-eval-dataset.yaml` (45 in_corpus · 22 out_of_corpus ·
13 adversarial) · Issue #142 · `Docs/10_Kalibrierungsbericht.md` («Methodische Hinweise») ·
`R00_Baseline.md` (15 von 80).

### 4 · Lokale Modelle: die Qualität ist da

**Aussage geändert am 20.09.** Vorher hiess die Folie «machbar, noch nicht gut genug». Das war
zu pauschal: Gemessen erfüllt **kein** Modell beide Grenzen — auch die Cloud-Referenz nicht, die
bei den fälschlich abgelehnten Antworten 22,2 % statt der geforderten 15 % liefert. Ein
Massstab, den das eigene Referenzmodell reisst, taugt nicht zur Abwertung der lokalen.

**Sagen:** Fünf Modelle durch dieselbe Pipeline. Das beste lokale Modell — gemma4 mit 26
Milliarden Parametern — erfindet nichts, hält unser Ausgabeprotokoll zu 100 % ein (die Referenz:
93 %) und lehnt nur 11,1 % der richtigen Antworten fälschlich ab, also halb so viele wie die
Referenz. Bei der Ablehnung fremder Fragen fehlt ihm genau eine Frage von 22: 19 statt 20.

**Die zwei Fehler, die unsere sind:** Zwei Antworten liefen ins Token-Limit und kamen leer
zurück (Klasse A in der Fehlerauswertung), weil `max_answer_tokens` zu tief stand. Für die
nächste Runde ist die Erhöhung auf 12 000 bereits notiert.

**Ein Modellwechsel ist trotzdem kein Komponententausch:** Das Modell muss das Ausgabeprotokoll
bedienen — «Weiss ich nicht», Belegnummern in eckigen Klammern, das Urteil der Selbstprüfung.
gpt-oss hält es nur zu 81 % ein; ein Modell kann inhaltlich richtig urteilen und trotzdem als
Fehler zählen.

**Und «lokal» ist keine Eigenschaft, sondern modellspezifisch:** gpt-oss und ministral lehnen
38 bis 40 % der richtigen Antworten fälschlich ab — mit denen wäre LearnFlow unbrauchbar. Die
Aussage gilt für *ein* Modell, nicht für die Kategorie. Wer das im Publikum zuspitzt, bekommt
diesen Satz.

**Zur Hardware — was auf der Folie steht und was dahinter:**

- Gemessen wurde bewusst am unteren Ende: eine Karte mit 8 GB Grafikspeicher. gemma4 belegt
  18 GB, läuft also teilweise auf der CPU; daher 58 Sekunden Median pro Antwort gegen die
  Vorgabe p95 ≤ 10 s.
- Damit das Modell mit 16K-Kontext vollständig in den Grafikspeicher passt, braucht es
  **24 GB**; mit Reserve für grösseren Kontext oder ein grösseres Modell 48 GB.
- **Preisrahmen, Grössenordnung (Stand Anfang 2026, vor einer Beschaffung prüfen):** eine
  einzelne 24-GB-Karte der aktuellen Consumer-Generation liegt bei rund 2000–3000 Franken,
  zwei gebrauchte 24-GB-Karten deutlich darunter; als kompletter Arbeitsplatzrechner mit
  Netzteil, Board und Speicher landet man bei **rund 3000 bis 6000 Franken**. Professionelle
  48-GB-Karten liegen ein Vielfaches darüber und sind für diesen Zweck nicht nötig.
- **Wichtig zu sagen, wenn nachgefragt wird:** Die Geschwindigkeit auf solcher Hardware haben
  wir **nicht gemessen** — sie ist eine begründete Erwartung. gemma4 erzeugt zudem viele
  unsichtbare Denk-Tokens; es wird auch auf guter Hardware kein schnelles Modell sein. Wer
  Tempo braucht, schaut eher auf ein kleineres Modell mit derselben Disziplin.

**Einordnung zum Schluss:** Für den Pilot ist Azure OpenAI EU gesetzt (ADR-004) — aus
Datenschutzgründen, nicht aus Qualitätsgründen. Lokal ist damit kein Notnagel, sondern die
nächste Stufe.

**Belege:** `kennzahlen.csv` alle 23 Läufe (gemma4 R01 sogar 6,7 % fälschlich abgelehnt;
Protokolltreue R04 = 1,000; Urteilsfähigkeit 0,983 — beides die besten Werte im Feld) ·
`EvalAnalysis/Optimierung/Modelle.md` («Testhardware», Beobachtungen zu gemma4 R04) · Issue #136.

### 5 · Erst der Massstab, dann der grösste Hebel

**Zwei Punkte, mehr nicht** (Entscheid vom 20.09.: die Folie war mit vier Punkten zu brav).

**1 · Gold muss Gold sein.** Mehr Testfragen — und jede einzelne gegen die Quelle geprüft. Das
Bild dazu: zwei Medaillen, Gold und Bronze. Der Satz dazu: «Drei unserer Einträge waren Bronze,
und im Dataset sieht man das keinem an.» Damit schliesst sich der Bogen zu Folie 3, wo der
Bronze-Eintrag im Wortlaut stand.

**2 · Die Auswahl schlägt die Suche.** 13 von 15 fehlenden Quellen lagen schon in der
Kandidatenliste — nur nicht unter den fünf Abschnitten, die das Modell sieht. Besser auswählen
statt besser suchen: bis zu 17 Prozentpunkte. Das ist derselbe Befund, den Block 2 an Q1 gezeigt
hat, und der grösste Hebel der ganzen Analyse.

**Falls zum Re-Ranker nachgefragt wird:** Eine Auswahl nach Inhalt statt nach Platz in zwei
Ranglisten. Dazu die Architekturfrage: ADR-005 hält schwere ML-Bibliotheken aus dem Backend;
bleiben ein zusätzlicher Modellaufruf oder ein weiterer Anbieter — und damit eine
Datenschutzfrage vor dem Pilot. **Nicht gemessen**, das wäre die nächste Runde.

**Der Rest steht klein am Fuss der Karte** und wird höchstens gestreift: Prüfung automatisch bei
jeder Änderung (T-53), Konfiguration an einer Stelle (T-64), vor dem Pilot der Wechsel auf Azure
OpenAI EU.

**Retos Vorgabe einhalten:** keine Zeitangaben, keine Deadlines. «Offen, weil anderes vorging» —
nicht «leider nicht geschafft».

**Schlusssatz, langsam:** «Keine Antwort ohne Beleg — das hält. Was wir dazugelernt haben: Der
Beleg dafür, dass es hält, ist die eigentliche Arbeit.» Danach Übergabe an die Fragerunde.

---

## Bewusst nicht auf den Folien

| Thema | Warum nicht | Wenn gefragt wird |
|---|---|---|
| Strenge Halluzinationsrate (2,9 %) | Entscheid vom 20.09. | Antwort bei Folie 1 |
| Ergebnis des ersten Kalibrierungslaufs | positiv erzählen: Werkzeug und nächster Schritt statt Zwischenstand | Antwort bei Folie 2 |
| **Stufe 0 und 1 blockieren nie** (gestrichen am 20.09.) | zu sehr Innensicht für die Schlussminuten | «Zwei der vier Prüfstufen haben über alle Läufe keine einzige Frage gestoppt — ihre Schwellenwerte liegen unter dem, was in der Praxis vorkommt. Entweder sie bekommen aus der Kalibrierung wirksame Werte, oder sie werden durch eine inhaltliche Vorprüfung ersetzt.» (`Pipeline-Review.md`, Befunde 1/3/4) |
| Re-Ranker als eigene Folie (gestrichen) | steht als Punkt 3 der nächsten Schritte | Details bei Folie 5 |
| Die Wortsuche im Detail | steht in Block 2, Folien 8–11 | — |
| Die vier Optimierungsrunden einzeln | Projektgeschichte, kein Ausblick | Kurzfassung bei Folie 2 |
| Schwellen je Modell, MMR, Coverage senken | gemessen und verworfen | bei Coverage 0,25 kämen sieben Antworten frei, zwei davon falsch |
| Zeitangaben, Deadlines, Stundenzahlen | Retos Vorgabe | — |

## Offene Entscheide

1. **Gesamtzeit.** Block 2 rund 9 Minuten, Block 5 rund 5. Retos Plan sieht 6–7 und 1–2 vor.
   Der naheliegendste Ausgleich ist die Demo (8–9 Minuten, Quiz dort als «evtl. streichen»
   markiert). **Mit Reto klären.**
2. **Folie 3 mit Frank abstimmen** — er hat das Gold-Dataset abgenommen (T-48). Die Folie soll
   als gemeinsamer Befund klingen, nicht als Kritik; Formulierung dafür steht oben.
3. **Christophs Learnings-Folie 2 (T-28)** — zwei Ungenauigkeiten, Details in
   [`Archive/Block5_Notizen.md`](Archive/Block5_Notizen.md), Abschnitt «Offene Entscheide».
4. **Wie viel Halluzinations-Ehrlichkeit?** Aktuell: nichts auf der Folie, saubere Antwort auf
   Nachfrage. Wenn Frank es anders sieht, ist Folie 1 die Stelle dafür.
