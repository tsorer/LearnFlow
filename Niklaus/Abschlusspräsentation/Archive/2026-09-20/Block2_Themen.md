# Block 2 — Themenübersicht (top down)

Arbeitspapier für den Neuaufbau. Noch keine Folien: erst entscheiden, **was** in Block 2
gehört, dann bauen. Der Stand vom 19.09. (`Archive/`, 19 Folien, ~10:25) war zu 100 %
der Antwortweg — ein Weg von dreien durch das System.

---

## 1 · Wozu dient Block 2?

Reto setzt 6–7 Minuten an, direkt nach der Demo. Das Publikum hat dann gesehen:
Dokument hoch, Frage gestellt, Antwort mit Quelle, «weiss ich nicht», Konfidenz-Badge,
Feedback. Block 2 muss genau eine Frage beantworten:

> **Wie ist gebaut, was ihr gerade gesehen habt — und warum darf man dem trauen?**

Daraus folgen drei Prüfsteine für jedes Thema unten:

1. **Erklärt es etwas, das in der Demo sichtbar war?** (Retos Leitidee: nur zeigen, was
   die Demo erklärt)
2. **Ist es eine technische Entscheidung, nicht nur eine Beschreibung?** Ein Publikum aus
   Dozierenden und Peers hört «FastAPI und React» in jeder zweiten Präsentation. Interessant
   ist, wo wir uns *anders* entschieden haben und warum.
3. **Haben wir einen Beleg dafür?** Zahl, Messung oder Codeort — sonst ist es eine Behauptung.

---

## 2 · Die Landkarte: drei Wege durch dasselbe System

Der Rahmen, der bisher fehlte. Alles, was wir gebaut haben, liegt auf einem von drei Wegen:

| Weg | Wer löst ihn aus | Was passiert | Wo die Qualität entschieden wird |
|---|---|---|---|
| **A · Wissen hinein** | Stefan lädt ein Dokument hoch | Parsen → Stückeln → Einbetten → Indexieren | beim Stückeln: schlechte Abschnitte kann keine Suche retten |
| **B · Frage hinein, Antwort heraus** | Lara fragt | Suchen → Mischen → Prüfen → Antworten → Nachprüfen | in vier Prüfstufen, fail-closed |
| **C · Fragen hinaus** (Quiz) | Stefan drückt «generieren» | Stichprobe → Modell schlägt 5 Fragen vor → Mensch gibt frei | beim **Menschen**, nicht bei einem Score |

Dazu ein Querschnitt, der auf allen drei Wegen gilt: **Belege** (Eval), **Betrieb**
(Rollen, Limits, Konfiguration) und **Vertrag** (OpenAPI).

Diese Tabelle ist mein Vorschlag für die zweite Folie des Blocks — sie macht sofort klar,
dass die Pipeline nicht das ganze System ist, und gibt der restlichen Zeit eine Struktur.

---

## 3 · Themenkatalog

Jedes Thema mit: was es ist · warum es technisch interessant ist · was wir als Beleg
haben · geschätzte Redezeit · mein Urteil.

### T1 · Container-Landkarte (C4-C2)

- **Was:** vier Container — `webapp / api / worker / db`, Docker Compose.
- **Interessant:** drei getrennte Netze; **API und Worker teilen kein Netz**. Der Worker ist
  nicht über die API erreichbar, die Warteschlange läuft über die Datenbank. Und: kein Redis,
  keine eigene Vektordatenbank — Postgres macht vier Jobs gleichzeitig (relational, Vektoren
  via pgvector/HNSW, deutscher Volltext via tsvector/GIN, Queue via pgqueuer).
- **Beleg:** `Docs/05_C4-C2_Container.md`, ADR-001/003/006; Diagramm existiert (Archive-Folie 1).
- **Zeit:** 0:45 · **Urteil: Kern.** Ohne Landkarte hängt alles andere in der Luft.

### T2 · Weg A: vom PDF zum durchsuchbaren Abschnitt

- **Was:** Upload (max. 10 MB, als `bytea` in der DB) → Job in der Warteschlange → Parsen
  (PDF/DOCX/Markdown) → strukturbewusstes Stückeln (512 Tokens, 64 Überlappung) → Einbetten
  → Index. Status wandert sichtbar durch die Oberfläche (das war in der Demo zu sehen).
- **Interessant:**
  - Die **Herkunft wird beim Parsen mitgeführt** (Seite, Absatz) — nur deshalb kann der
    Quellenlink später die Stelle im Originaldokument markieren.
  - **Stückeln an natürlichen Grenzen** (Überschrift > Absatz > Satz > Zeile > Wort), erst
    bei Überlänge feiner. Kein Abschnitt endet mitten im Satz.
  - Der Token-Zähler ist **derselbe wie beim Embedding-Modell** (cl100k_base) — sonst zählt
    man etwas anderes, als der Anbieter abschneidet.
  - Nebenbefund aus unserem Trace: **Seitengrenzen sind harte Schnittgrenzen.** Die Antwort
    auf unsere Beispielfrage steht deshalb in zwei Abschnitten (OBV S. 12, Teil 1 und 2).
- **Beleg:** `services/parsing.py`, `services/chunking.py`, `Pipeline-Trace/`.
- **Zeit:** 1:00–1:15 · **Urteil: Kern, neu.** Das fehlte bisher komplett und erklärt die
  Demo-Szene «Dokument hochladen» — und erklärt später, warum Retrieval überhaupt Mühe hat.

### T3 · Weg B: die Antwort-Pipeline

- **Was:** Suchen (Bedeutung + Wörter) → Mischen (RRF) → Vorprüfung → Antworten → Nachprüfung.
  Vier Stufen, neun mögliche Ausgänge, zwei davon rufen ein Sprachmodell.
- **Interessant:** fail-closed — jede Stufe darf unterdrücken, keine darf aufwerten. «Weiss
  ich nicht» ist ein Ergebnis, kein Fehler.
- **Beleg:** vollständig. Zwei echte Läufe mit allen Zwischenwerten (`Pipeline-Trace/Q1.json`,
  `Q2.json`), 19 fertige Folien im Archiv.
- **Zeit:** bisher 6:30 in 12 Folien · **Urteil: Kern — aber auf 2:30–3:00 eindampfen.**
  Siehe Abschnitt 5: Was vom alten Block 2 überlebt.

### T4 · Weg C: Fragegenerierung mit menschlichem Gate

- **Was:** Stefan löst die Generierung aus. Das System zieht **10 zufällige Abschnitte** aus
  dem Bereich, das Modell macht daraus in *einem* Aufruf **5 Multiple-Choice-Fragen** mit je
  4 Optionen und einer Erklärung.
- **Interessant — und der stärkste neue Inhalt:**
  - **Die Reserve ist Absicht:** 10 Abschnitte für 5 Fragen. Mit genau 5 müsste das Modell
    auch aus einem Inhaltsverzeichnis eine Frage pressen. Unbenutzte Abschnitte sind der
    Normalfall, kein Fehler.
  - **Provenienz-Pflicht:** Jede Frage muss den Abschnitt nennen, aus dem sie stammt. Nennt
    sie eine Nummer, die es nicht gibt, wird die Frage **verworfen**, nicht mit geratener
    Quelle gespeichert. Das ist exakt dieselbe Regel wie `citation_invalid` im Antwortweg —
    eine erfundene Referenz ist ein Modellfehler, und keine Schwelle macht ihn akzeptabel.
  - **Das Gate ist ein Mensch.** Fragen landen als `pending` und bleiben dort. Kein
    Konfidenzwert entscheidet, ob eine Frage eine Lernende je sieht — Stefan gibt frei,
    lehnt ab oder **korrigiert den Text**. Fail-closed heisst hier: ohne Freigabe passiert
    nichts.
  - **Kein Wert ist nullbar, kein leerer Patch:** Wer korrigiert, muss etwas hinschreiben.
  - **Sichtbarkeit ist fail-closed:** Ein Filter kann die erlaubte Menge nur *verkleinern*,
    nie vergrössern. Eine Lernende, die nach `pending` filtert, bekommt eine leere Seite —
    keinen 403, aber auch keine unfreigegebene Frage.
  - Temperatur 0, kein Retry: Zwei Läufe unterscheiden sich, weil andere Abschnitte gezogen
    werden — nicht, weil das Modell würfelt.
- **Beleg:** `services/quiz.py` (Docstring ist die halbe Sprechnotiz), `routers/quiz.py`.
- **Zeit:** 1:00 · **Urteil: Kern, neu.** Zeigt, dass wir zwei verschiedene Gate-Arten
  bewusst unterscheiden: Maschine prüft die Antwort, Mensch prüft die Frage.

### T5 · Belege statt Behauptung: Eval und Kalibrierung

- **Was:** Gold-Dataset mit 80 Fragen (45 im Korpus, 22 ausserhalb, 13 adversarial), drei
  harte Gates (Halluzination 0 %, Ablehnung ausserhalb ≥ 90 %, falsche Unterdrückung ≤ 15 %).
  Dazu der Kalibrierungs-Loop: Schwellen **messen statt raten** (Snapshot + Offline-Replay).
- **Interessant:** Zwei Ebenen. (a) Woher weiss man, dass eine RAG-Pipeline funktioniert?
  (b) Was ist «Gold» überhaupt wert — unser eigener Gold-Defekt `SAMW-OOC-03` ist das ehrliche
  Beispiel: Die Antwort steht im Korpus, das Gold sagt «nicht enthalten».
- **Beleg:** ADR-009, `Docs/10_Kalibrierungsbericht.md`, Issue #142, fertige Folien im Archiv.
- **Zeit:** 1:15 · **Urteil: Kern.** Retos Gliederung nennt das explizit als das Neue
  gegenüber dem Architektur-Pitch. Ohne das ist «Halluzinationsrate ≈ 0 %» eine Behauptung.

### T6 · Laufzeit-Konfiguration ohne Deployment

- **Was:** Die Schwellenwerte stehen in der Datenbank und werden **pro Anfrage** gelesen.
  Admin ändert, Wirkung sofort.
- **Interessant:** Der Umgang mit Fehlern. Fehlende Zeile → Default (niemand hat etwas
  gewollt). Vorhandene, aber kaputte Zeile → **Fehler**, nicht der lockerere Default (jemand
  wollte etwas, und es ging schief). Das ist fail-closed in zwei Zeilen erklärt.
- **Beleg:** `services/config.py`, ADR-008 Nachtrag 2026-08-16.
- **Zeit:** 0:30 · **Urteil: Wenn Zeit.** Hängt davon ab, ob Reto das Admin-Panel in der Demo
  zeigt — wenn ja, gehört der Satz hierher; wenn nein, weglassen.

### T7 · Rollen, Isolation, Limits

- **Was:** drei Rollen (`learner`, `knowledge_owner`, `admin`), JWT, Bereichs-Trennung.
- **Interessant:** Das Rate-Limit ist **pro Konto**, nicht pro IP — die Pilotnutzer sitzen
  hinter einer NAT-Adresse, ein Vielfrager würde sonst das ganze Büro aussperren. Der Login
  zählt weiterhin pro IP, weil es dort noch kein Konto gibt.
- **Beleg:** `app/limiter.py` (Docstring), `Docs/03_QualityAttributes.md`.
- **Zeit:** 0:30 · **Urteil: Wenn Zeit** — oder ein Satz im Vorbeigehen auf der Landkarte.
  Passt auch gut in Franks Block (Security/Ethik Modul 8).

### T8 · API-First: der Vertrag zwischen den Hälften

- **Was:** `openapi.yaml` ist verbindlich, Frontend-Typen werden daraus generiert, ein Test
  prüft Spec gegen Code in **beide** Richtungen.
- **Interessant:** Das ist der Grund, warum zwei Leute gleichzeitig an Frontend und Backend
  arbeiten konnten, ohne sich abzusprechen — und es ist eine CI-Regel, keine Absichtserklärung.
- **Beleg:** ADR-010, `tests/test_rbac.py`, `CLAUDE.md`.
- **Zeit:** 0:30 · **Urteil: eher Frank (Block 3).** Das ist Arbeitsweise, nicht Architektur.
  Mit ihm absprechen, damit es nicht zweimal kommt.

### T9 · Kleinere Themen — bewusst nicht als eigene Folie

| Thema | Warum nicht | Wo es trotzdem vorkommen darf |
|---|---|---|
| Batch statt SSE (ADR-002) | erklärt nichts, was die Demo zeigte | Nebensatz auf der Landkarte |
| LiteLLM als Abstraktion, Wechsel auf Azure EU | wichtig fürs Produkt, aber kein Aufbau | Block 5 (Ausblick), dort steht es schon |
| Soft-Hyphen-Reparatur beim PDF-Parsen | schöne Anekdote, zu klein für eine Folie | mündlich bei T2, wenn jemand nachfragt |
| Feedback-Erfassung (👍/👎) | in der Demo selbsterklärend | – |
| Quellenlink mit Kontextfenster | war in der Demo sichtbar; erklärt sich über T2 (Herkunft) | ein Satz bei T2 |
| Determinismus (Temperatur 0, kein Retry) | Detail | je ein Halbsatz bei T3 und T4 |

---

## 4 · Vorschlag für den Schnitt

### Variante «Retos Budget» — 6:30

| # | Thema | Zeit |
|---|---|---|
| 1 | Landkarte: vier Container, eine Datenbank für vier Jobs (T1) | 0:45 |
| 2 | Drei Wege durch das System (Abschnitt 2) | 0:30 |
| 3 | Weg A: vom PDF zum Abschnitt (T2) | 1:00 |
| 4 | Weg B: die Pipeline in einem Bild + **ein** Moment aus dem Beispiel (T3) | 2:00 |
| 5 | Weg C: Maschine schlägt vor, Mensch gibt frei (T4) | 1:00 |
| 6 | Woher wir wissen, dass es hält: Gold-Dataset (T5) | 1:15 |

Querschnitt (T6/T7) als je ein Satz auf Folie 1, T8 geht an Frank.

### Variante «wenn 9–10 Minuten drin liegen»

Dieselbe Reihenfolge, aber Weg B bekommt 4:00 statt 2:00 und damit das Beispiel Q1/Q2 in der
ausgebauten Form (Suchen → Mischen → Stufen → was Lara sieht), plus T6 als eigene halbe Folie.
**Das ist eine Frage an Reto, keine Bauentscheidung** — ich kann beide Varianten aus demselben
Skript bauen.

---

## 5 · Was vom alten Block 2 überlebt

Aus `Archive/Block2_Technischer-Aufbau_v2.html` (19 Folien):

- **Bleibt direkt:** Architektur-Folie (1), Pipeline-Überblick (4), Stufen-Logik verdichtet,
  Eval-Gerüst (18), «Gold muss Gold sein» (19).
- **Wird eingedampft:** die fünf Such-Folien (5–9) und die drei Misch-/Vorprüf-Folien (10–12)
  auf zusammen ~2 Folien. Der Kerngedanke bleibt: Bedeutungssuche findet beide Fragen, die
  Wortsuche keine — und «das Gesetz spricht eine andere Sprache».
- **Wandert nach Block 5:** die Erkenntnis «Wortsuche kann schaden» (steht dort schon).
- **Kommt neu dazu:** T2 (Weg A) und T4 (Weg C) — zusammen rund 2 Minuten.

Das Archiv bleibt unangetastet; die neuen Folien entstehen in diesem Ordner mit einem eigenen
Build-Skript.

---

## 6 · Offene Fragen, bevor gebaut wird

1. **Zeitbudget:** 6–7 Minuten wie bei Reto, oder darf Block 2 länger? Davon hängt ab, wie
   viel vom Beispiel Q1/Q2 überlebt.
2. **Zeigt die Demo das Quiz?** Reto notiert «Quiz evtl. streichen». Wird es gestrichen, ist
   T4 in Block 2 umso wichtiger (sonst kommt die Fragegenerierung gar nicht vor) — oder es
   fällt mit, wenn wir es nicht erklären wollen.
3. **Zeigt die Demo das Admin-Panel?** Entscheidet über T6.
4. **Abgrenzung zu Frank:** T8 (API-First, CI) und T7 (Security/Ethik) — wer sagt was?
5. **Abgrenzung zu Christoph:** Er erzählt T-28 (Sparse-Stärke) als Learning. Unsere Messung
   dazu steht in Block 5. Block 2 sollte die Wortsuche deshalb erklären, aber nicht bewerten.
