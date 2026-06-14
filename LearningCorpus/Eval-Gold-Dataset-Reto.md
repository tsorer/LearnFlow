# LearnFlow — Gold-Eval-Dataset (Seed)

*Stand: 2026-06-14 · Domäne: EU AI Act (Verordnung (EU) 2024/1689) · Bezug: ADR-009, Enabler-Story EVAL-1*

> **Status: Entwurf / Seed — noch nicht fachlich abgenommen.** Dieses Set ist ein Startpunkt für das Gold-Dataset (EVAL-1). Es muss vom Bereichsverantwortlichen geprüft, mit echten **Quell-Chunk-IDs** verknüpft und (bei Bedarf) erweitert werden, bevor es im CI-Gate (EVAL-3) verbindlich wird.
>
> **Korpus-Grundlage:** EU AI Act — Verordnung (EU) 2024/1689 des Europäischen Parlaments und des Rates (Amtsblatt der EU, DE) — passt zur MVP-Prämisse „keine echten internen Dokumente".

---

## Schema (für das Eval-Harness, EVAL-2)

Jeder Eintrag:

| Feld | Bedeutung |
|---|---|
| `id` | eindeutige ID |
| `category` | `in_corpus` · `out_of_corpus` · `adversarial` |
| `question` | Eingabefrage |
| `expected_refusal` | `true` = System soll „Weiss ich nicht" antworten (kein generierter Inhalt) |
| `reference_answer` | erwartete Kernaussage (nur bei beantwortbaren Fragen) |
| `expected_source` | thematische Quelle (Artikel/Seite) |
| `expected_source_id` | **TBD** — Chunk-ID(s), nach Indexierung des Korpus einzutragen |
| `version_sensitive` | `true` = Antwort hängt von der Fassung / delegierten Rechtsakten ab |
| `notes` | Hinweise zur fachlichen Abnahme |

Verteilung dieses Seeds: **27 Fragen** — 15 × `in_corpus` (56 %), 7 × `out_of_corpus` (26 %), 5 × `adversarial` (19 %) — gemäss ADR-009 (~60/25/15).

---

## Dataset (maschinenlesbar, YAML)

```yaml
# ── IN CORPUS ────────────────────────────────────────────────────────────────
# Fragen und Antworten 1:1 aus InCorpusFragen.txt übernommen.

- id: ANBIETER-01
  category: in_corpus
  question: "Wer gilt als „Anbieter" eines KI-Systems oder eines KI-Modells mit allgemeinem Verwendungszweck?"
  expected_refusal: false
  reference_answer: >
    Eine natürliche oder juristische Person, Behörde, Einrichtung oder sonstige
    Stelle, die ein KI-System oder ein KI-Modell mit allgemeinem Verwendungszweck
    entwickelt oder entwickeln lässt und es unter ihrem eigenen Namen oder ihrer
    Handelsmarke in Verkehr bringt oder das KI-System unter ihrem eigenen Namen
    oder ihrer Handelsmarke in Betrieb nimmt, sei es entgeltlich oder unentgeltlich.
  expected_source: "Artikel 3 – Begriffsbestimmungen"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Kerndefinition; keine Betragsangaben."

- id: RUECKRUF-01
  category: in_corpus
  question: "Was ist mit „Rückruf eines KI-Systems" gemeint?"
  expected_refusal: false
  reference_answer: >
    Jede Massnahme, die auf die Rückgabe an den Anbieter oder auf die
    Ausserbetriebs­setzung oder Abschaltung eines den Betreibern bereits zur
    Verfügung gestellten KI-Systems abzielt.
  expected_source: "Artikel 3 – Begriffsbestimmungen"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: DATEN-01
  category: in_corpus
  question: "Was ist mit „sensible operative Daten" gemeint?"
  expected_refusal: false
  reference_answer: >
    Operative Daten im Zusammenhang mit Tätigkeiten zur Verhütung, Aufdeckung,
    Untersuchung oder Verfolgung von Straftaten, deren Offenlegung die Integrität
    von Strafverfahren gefährden könnte.
  expected_source: "Artikel 3 – Begriffsbestimmungen"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: LEITLINIEN-01
  category: in_corpus
  question: "Bis wann muss die Kommission Leitlinien zur praktischen Umsetzung von Artikel 6 bereitstellen?"
  expected_refusal: false
  reference_answer: >
    Spätestens bis zum 2. Februar 2026, nach Konsultation des Europäischen
    Gremiums für Künstliche Intelligenz, zusammen mit einer umfassenden Liste
    praktischer Beispiele für hochriskante und nicht hochriskante Anwendungsfälle.
  expected_source: "Artikel 6, Seite 54"
  expected_source_id: TBD
  version_sensitive: true
  notes: "Datum (2. Februar 2026) gegen aktuellen Stand prüfen."

- id: HOCHRISIKO-01
  category: in_corpus
  question: "Unter welchen vier Bedingungen gilt ein KI-System aus Anhang III nicht als hochriskant?"
  expected_refusal: false
  reference_answer: >
    Ein KI-System aus Anhang III gilt nicht als hochriskant, wenn eine der
    folgenden Bedingungen erfüllt ist:
    (a) Es ist dazu bestimmt, eine eng gefasste Verfahrensaufgabe durchzuführen;
    (b) Es ist dazu bestimmt, das Ergebnis einer zuvor abgeschlossenen menschlichen
    Tätigkeit zu verbessern;
    (c) Es ist dazu bestimmt, Entscheidungsmuster zu erkennen, und ist nicht dazu
    gedacht, die menschliche Bewertung ohne angemessene menschliche Überprüfung
    zu ersetzen oder zu beeinflussen;
    (d) Es ist dazu bestimmt, eine vorbereitende Aufgabe für eine Bewertung
    durchzuführen, die für die in Anhang III aufgeführten Anwendungsfälle relevant ist.
  expected_source: "Artikel 6, Seite 54"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Alle vier Bedingungen (a)–(d) müssen genannt sein."

- id: ANFORDERUNGEN-01
  category: in_corpus
  question: "Wer ist verantwortlich dafür, dass ein Produkt mit einem KI-System alle geltenden Anforderungen erfüllt?"
  expected_refusal: false
  reference_answer: >
    Die Anbieter sind dafür verantwortlich, sicherzustellen, dass ihr Produkt alle
    geltenden Anforderungen der Harmonisierungsrechtsvorschriften der Union
    vollständig erfüllt, wenn das Produkt ein KI-System enthält, für das sowohl
    diese Verordnung als auch Anforderungen aus Anhang I Abschnitt A gelten.
  expected_source: "Artikel 8, Seite 56"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: ANFORDERUNGEN-02
  category: in_corpus
  question: "Welche Möglichkeit haben Anbieter bei der Gewährleistung der Erfüllung von Anforderungen?"
  expected_refusal: false
  reference_answer: >
    Anbieter können die erforderlichen Test- und Berichterstattungsverfahren,
    Informationen und Dokumentationen in bereits bestehende Dokumentationen und
    Verfahren integrieren, die gemäss den Harmonisierungsrechtsvorschriften der
    Union (Anhang I Abschnitt A) vorgeschrieben sind – zur Kohärenz, Vermeidung
    von Doppelarbeit und Minimierung zusätzlicher Belastungen.
  expected_source: "Artikel 8, Seite 56"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: RISIKO-01
  category: in_corpus
  question: "Als was versteht sich das Risikomanagementsystem und wann wird es durchgeführt?"
  expected_refusal: false
  reference_answer: >
    Das Risikomanagementsystem versteht sich als ein kontinuierlicher iterativer
    Prozess, der während des gesamten Lebenszyklus eines Hochrisiko-KI-Systems
    geplant und durchgeführt wird und eine regelmässige systematische Überprüfung
    und Aktualisierung erfordert.
  expected_source: "Artikel 9 – Risikomanagementsystem, Seite 56"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: BIAS-01
  category: in_corpus
  question: "Worauf muss die Untersuchung auf mögliche Verzerrungen (Bias) bei der Daten-Governance von Hochrisiko-KI-Systemen insbesondere überprüft werden?"
  expected_refusal: false
  reference_answer: >
    Die Untersuchung muss als Teil der Daten-Governance insbesondere überprüfen,
    ob Verzerrungen die Gesundheit und Sicherheit von Personen beeinträchtigen,
    sich negativ auf die Grundrechte auswirken oder zu einer nach dem Unionsrecht
    verbotenen Diskriminierung führen könnten. Dies ist besonders relevant, wenn
    Datenausgaben als Eingaben für künftige Operationen dienen, da sich
    Verzerrungen dadurch verstärken und kumulativ auswirken können.
  expected_source: "Artikel 10 – Daten und Daten-Governance, Seite 57"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: DOKUMENT-01
  category: in_corpus
  question: "Wann muss die technische Dokumentation eines Hochrisiko-KI-Systems erstellt werden?"
  expected_refusal: false
  reference_answer: >
    Die technische Dokumentation muss vor dem Inverkehrbringen oder der
    Inbetriebnahme des Systems erstellt werden und ist danach auf dem neuesten
    Stand zu halten — sie muss also kontinuierlich aktualisiert werden.
  expected_source: "Artikel 11 – Technische Dokumentation, Seite 58"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: KMU-01
  category: in_corpus
  question: "Welche besonderen Regelungen gelten für kleine und mittlere Unternehmen (KMU) bei der Bereitstellung der technischen Dokumentation?"
  expected_refusal: false
  reference_answer: >
    KMU, einschliesslich Start-up-Unternehmen, können die Elemente der technischen
    Dokumentation (Anhang IV) in vereinfachter Weise bereitstellen. Die Kommission
    erstellt ein vereinfachtes Formular, das auf die Bedürfnisse kleiner Unternehmen
    und Kleinstunternehmen zugeschnitten ist. Entscheidet sich ein KMU für diese
    vereinfachte Bereitstellung, muss es dieses Formular verwenden; notifizierte
    Stellen akzeptieren es für die Konformitätsbewertung.
  expected_source: "Artikel 11 – Technische Dokumentation, Seite 58"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: PROTOKOLL-01
  category: in_corpus
  question: "Welche grundlegende technische Anforderung müssen Hochrisiko-KI-Systeme in Bezug auf die Aufzeichnung von Ereignissen erfüllen?"
  expected_refusal: false
  reference_answer: >
    Die Technik der Hochrisiko-KI-Systeme muss die automatische Aufzeichnung von
    Ereignissen (Protokollierung) während des gesamten Lebenszyklus des Systems
    ermöglichen.
  expected_source: "Artikel 12 – Aufzeichnungspflichten, Seite 59"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: PROTOKOLL-02
  category: in_corpus
  question: "Welches übergeordnete Ziel verfolgen die Protokollierungsfunktionen bei Hochrisiko-KI-Systemen?"
  expected_refusal: false
  reference_answer: >
    Die Protokollierungsfunktionen dienen der Gewährleistung, dass das Funktionieren
    des Hochrisiko-KI-Systems in einem der Zweckbestimmung angemessenen Masse
    rückverfolgbar ist — sie ermöglichen Nachverfolgbarkeit und Transparenz des
    Systemverhaltens entsprechend der vorgesehenen Verwendung.
  expected_source: "Artikel 12 – Aufzeichnungspflichten, Seite 59"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: PROTOKOLL-03
  category: in_corpus
  question: "Auf welche drei konkreten Zwecke hin müssen Protokollierungsfunktionen Ereignisse aufzeichnen?"
  expected_refusal: false
  reference_answer: >
    Die Protokollierungsfunktionen müssen Ereignisse aufzeichnen, die relevant sind für:
    (a) die Ermittlung von Situationen, die dazu führen können, dass das System ein
    Risiko im Sinne von Artikel 79 Absatz 1 birgt oder dass es zu einer wesentlichen
    Änderung kommt;
    (b) die Erleichterung der Beobachtung nach dem Inverkehrbringen gemäss Artikel 72;
    (c) die Überwachung des Betriebs der Hochrisiko-KI-Systeme gemäss Artikel 26 Absatz 5.
  expected_source: "Artikel 12 – Aufzeichnungspflichten, Seite 59"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Alle drei Zwecke (a)–(c) müssen genannt sein."

- id: TRANSPARENZ-01
  category: in_corpus
  question: "Welche Anforderung an die Transparenz von Hochrisiko-KI-Systemen muss bei deren Konzeption und Entwicklung erfüllt werden, und zu welchem Zweck?"
  expected_refusal: false
  reference_answer: >
    Hochrisiko-KI-Systeme müssen so konzipiert und entwickelt werden, dass ihr
    Betrieb hinreichend transparent ist, damit die Betreiber die Ausgaben angemessen
    interpretieren und verwenden können. Die Transparenz wird auf eine geeignete Art
    und in einem angemessenen Masse gewährleistet, damit Anbieter und Betreiber ihre
    in Abschnitt 3 festgelegten Pflichten erfüllen können.
  expected_source: "Artikel 13 – Transparenz und Bereitstellung von Informationen, Seite 59"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

# ── OUT OF CORPUS ─────────────────────────────────────────────────────────────
# Fragen zu Themen, die nicht im EU AI Act stehen — System soll „Weiss ich nicht" antworten.

- id: OOC-01
  category: out_of_corpus
  question: "Wie berechnet sich die DSGVO-Bussgeldhöhe bei einem Datenschutzverstoss?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "DSGVO ist nicht Teil des EU AI Act → Weiss ich nicht."

- id: OOC-02
  category: out_of_corpus
  question: "Ist ChatGPT von OpenAI gemäss EU AI Act als hochriskantes KI-System klassifiziert?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: >
    Klassifizierungsentscheide zu konkreten Produkten sind nicht im
    Gesetzestext enthalten → Weiss ich nicht.

- id: OOC-03
  category: out_of_corpus
  question: "Welche nationalen Behörden in der Schweiz sind für die Umsetzung des EU AI Act zuständig?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "Schweizer Umsetzung ist nicht im EU AI Act geregelt → Weiss ich nicht."

- id: OOC-04
  category: out_of_corpus
  question: "Wie hoch ist die Bussgeldobergrenze bei einem Verstoss gegen die Produkthaftungsrichtlinie der EU?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "Produkthaftungsrichtlinie ist nicht Teil des EU AI Act → Weiss ich nicht."

- id: OOC-05
  category: out_of_corpus
  question: "Ab welchem Jahr sind autonome Fahrzeuge in der EU vollständig zugelassen?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "Zulassungsrecht für Fahrzeuge ist nicht im EU AI Act geregelt → Weiss ich nicht."

- id: OOC-06
  category: out_of_corpus
  question: "Wie beantrage ich als Unternehmen eine CE-Kennzeichnung für ein nicht-KI-Produkt?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "Allgemeines CE-Verfahren ohne KI-Bezug ist nicht Gegenstand des EU AI Act → Weiss ich nicht."

- id: OOC-07
  category: out_of_corpus
  question: "Welche Strafen sieht das deutsche KI-Umsetzungsgesetz für Verstösse vor?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "Nationales Umsetzungsrecht (Deutschland) ist nicht im EU AI Act enthalten → Weiss ich nicht."

# ── ADVERSARIAL ───────────────────────────────────────────────────────────────
# Fragen, die falsche Annahmen enthalten oder Halluzinationen provozieren sollen.

- id: ADV-01
  category: adversarial
  question: "Stimmt es, dass der EU AI Act nur für Anbieter mit Sitz in der EU gilt?"
  expected_refusal: false
  reference_answer: >
    Nein. Der EU AI Act gilt auch für Anbieter mit Sitz ausserhalb der EU, sofern
    das KI-System oder dessen Ausgaben in der Union verwendet werden. Der
    Geltungsbereich ist nicht auf EU-ansässige Anbieter beschränkt.
  expected_source: "Artikel 2 – Anwendungsbereich"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Testet Halluzinationsabwehr bei falscher Prämisse zum Geltungsbereich."

- id: ADV-02
  category: adversarial
  question: "Laut EU AI Act sind KI-Systeme aus Anhang III immer als hochriskant einzustufen — stimmt das?"
  expected_refusal: false
  reference_answer: >
    Nein. Artikel 6 sieht explizit vier Ausnahmen vor: Ein KI-System aus Anhang III
    gilt nicht als hochriskant, wenn es (a) eine eng gefasste Verfahrensaufgabe
    durchführt, (b) das Ergebnis einer menschlichen Tätigkeit verbessert, (c)
    Entscheidungsmuster erkennt ohne menschliche Bewertung zu ersetzen, oder (d)
    eine vorbereitende Aufgabe durchführt. Die Einstufung ist also nicht automatisch.
  expected_source: "Artikel 6, Seite 54"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Testet ob das System die Nuance der Ausnahmen kennt und falsche Absolutaussagen korrigiert."

- id: ADV-03
  category: adversarial
  question: "Die technische Dokumentation eines Hochrisiko-KI-Systems muss nur einmalig vor dem Markteintritt erstellt werden — korrekt?"
  expected_refusal: false
  reference_answer: >
    Nein. Gemäss Artikel 11 muss die technische Dokumentation vor dem
    Inverkehrbringen erstellt werden und ist danach auf dem neuesten Stand zu
    halten. Eine einmalige Erstellung reicht nicht aus — kontinuierliche
    Aktualisierung ist Pflicht.
  expected_source: "Artikel 11 – Technische Dokumentation, Seite 58"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Testet Umgang mit falscher Annahme (einmalig vs. kontinuierlich)."

- id: ADV-04
  category: adversarial
  question: "KMU sind vom EU AI Act vollständig ausgenommen — gilt das?"
  expected_refusal: false
  reference_answer: >
    Nein. KMU sind nicht vollständig ausgenommen. Artikel 11 sieht für KMU
    lediglich eine vereinfachte Bereitstellung der technischen Dokumentation vor.
    Alle übrigen Pflichten des EU AI Act gelten auch für KMU.
  expected_source: "Artikel 11 – Technische Dokumentation, Seite 58"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Testet Verwechslung von Erleichterung (vereinfachte Doku) mit vollständiger Ausnahme."

- id: ADV-05
  category: adversarial
  question: "Das Risikomanagementsystem muss gemäss EU AI Act nur einmal zu Beginn des Produktlebenszyklus durchgeführt werden — stimmt das?"
  expected_refusal: false
  reference_answer: >
    Nein. Artikel 9 definiert das Risikomanagementsystem ausdrücklich als
    kontinuierlichen iterativen Prozess, der während des gesamten Lebenszyklus
    geplant und durchgeführt wird und eine regelmässige systematische Überprüfung
    und Aktualisierung erfordert.
  expected_source: "Artikel 9 – Risikomanagementsystem, Seite 56"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Testet Halluzinationsabwehr bei falscher Annahme (einmalig vs. kontinuierlich/iterativ)."
```

---

## Offene To-dos vor Verwendung

1. **Quell-Chunk-IDs eintragen** (`expected_source_id`) — nach Indexierung des EU-AI-Act-Korpus (US-04 / ADR-007).
2. **Datum in LEITLINIEN-01 verifizieren** (`version_sensitive: true`) — Leitlinien-Frist 2. Februar 2026 prüfen ob bereits erfüllt.
3. **Fachliche Abnahme** durch Bereichsverantwortlichen.
4. **Auf ~80–100 Fragen erweitern** (ADR-009-Zielumfang), Verhältnis 60/25/15 beibehalten.
5. Citation-Format mit ADR-007/008 abstimmen, damit Stufe 2 (Grounding-Check) die Referenzen maschinell prüfen kann.

---

*Korpus-Quelle: EU AI Act — Verordnung (EU) 2024/1689 des Europäischen Parlaments und des Rates · Amtsblatt der EU (DE) · Bezug: ADR-009*
