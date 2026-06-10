# LearnFlow — Gold-Eval-Dataset (Seed)

*Stand: 2026-06-10 · Domäne: Schweizer Sozialhilfe (SKOS-Richtlinien) · Bezug: ADR-009, Enabler-Story EVAL-1*

> **Status: Entwurf / Seed — noch nicht fachlich abgenommen.** Dieses Set ist ein Startpunkt für das Gold-Dataset (EVAL-1). Es muss vom Bereichsverantwortlichen geprüft, mit echten **Quell-Chunk-IDs** verknüpft und (bei Bedarf) erweitert werden, bevor es im CI-Gate (EVAL-3) verbindlich wird.
>
> **Korpus-Grundlage:** SKOS-Richtlinien (öffentlich, deutschsprachig) — passt zur MVP-Prämisse „keine echten internen Dokumente".

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
| `expected_source` | thematische Quelle (Kapitel/Abschnitt) |
| `expected_source_id` | **TBD** — Chunk-ID(s), nach Indexierung des Korpus einzutragen |
| `version_sensitive` | `true` = Antwort hängt von der SKOS-Fassung ab (2021 vs. 1.1.2026) |
| `notes` | Hinweise zur fachlichen Abnahme |

Verteilung dieses Seeds: **26 Fragen** — 15 × `in_corpus` (58 %), 7 × `out_of_corpus` (27 %), 4 × `adversarial` (15 %) — gemäß ADR-009 (~60/25/15). Themen: Grundprinzipien, Grundbedarf, Wohnkosten, Integrationszulage/Einkommensfreibetrag, situationsbedingte Leistungen, Sanktionen, **Krankenversicherung & IPV** (medizinische Grundversorgung) sowie **vorrangige Leistungen** (Alimentenbevorschussung, Ergänzungsleistungen) als Subsidiaritäts-Grenzfälle.

---

## Dataset (maschinenlesbar, YAML)

```yaml
- id: GBL-01
  category: in_corpus
  question: "Was umfasst der Grundbedarf für den Lebensunterhalt (GBL)?"
  expected_refusal: false
  reference_answer: >
    Nahrung, Getränke/Tabak, Kleider und Schuhe, Energieverbrauch (ohne
    Wohn-Nebenkosten), Haushaltsführung, Körperpflege, lokaler Verkehr,
    Kommunikation/Internet, Radio/TV, Bildung sowie Freizeit/Sport/Unterhaltung.
  expected_source: "Kapitel Grundbedarf (GBL)"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Zusammensetzung; keine Beträge."

- id: GBL-02
  category: in_corpus
  question: "Wie hoch ist der Grundbedarf für einen 1-Personen-Haushalt pro Monat?"
  expected_refusal: false
  reference_answer: "CHF 1061 pro Monat (Stand 2025/2026)."
  expected_source: "Grundbedarf / Merkblatt Teuerung"
  expected_source_id: TBD
  version_sensitive: true
  notes: "Betrag gegen gewählte Fassung prüfen (Teuerungsanpassung)."

- id: PRINZ-01
  category: in_corpus
  question: "Nach welchem Grundprinzip wird Sozialhilfe nur gewährt, wenn keine anderen Mittel oder Ansprüche bestehen?"
  expected_refusal: false
  reference_answer: "Subsidiaritätsprinzip — Sozialhilfe ist nachrangig gegenüber Selbsthilfe, Ansprüchen Dritter und anderen Sozialleistungen."
  expected_source: "Allgemeiner Teil / Grundprinzipien"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: PRINZ-02
  category: in_corpus
  question: "Was bedeutet das Bedarfsdeckungsprinzip?"
  expected_refusal: false
  reference_answer: "Die Hilfe deckt den konkreten, aktuellen Bedarf in der Notlage; keine bedarfsunabhängige Pauschale."
  expected_source: "Grundprinzipien"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: IZU-01
  category: in_corpus
  question: "Wofür wird eine Integrationszulage (IZU) ausgerichtet?"
  expected_refusal: false
  reference_answer: "Als Anreiz/Anerkennung für Bemühungen zur sozialen und beruflichen Integration, insbesondere bei Nicht-Erwerbstätigen."
  expected_source: "Kapitel Integrationszulagen"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: EFB-01
  category: in_corpus
  question: "Was ist der Einkommensfreibetrag (EFB) bei Erwerbstätigkeit?"
  expected_refusal: false
  reference_answer: "Ein Teil des Erwerbseinkommens, der nicht an die Unterstützung angerechnet wird — als Erwerbsanreiz."
  expected_source: "Kapitel Einkommensfreibeträge"
  expected_source_id: TBD
  version_sensitive: true
  notes: "Konkrete Bandbreite versionsabhängig."

- id: SIL-01
  category: in_corpus
  question: "Welche Auslagen zählen zu den situationsbedingten Leistungen (SIL)?"
  expected_refusal: false
  reference_answer: "Individuell begründete Sonderkosten, z. B. krankheits-/behinderungsbedingte Auslagen, Erwerbsunkosten, Betreuungskosten."
  expected_source: "Kapitel Situationsbedingte Leistungen"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: WOHN-01
  category: in_corpus
  question: "Wie werden Wohnkosten in der Sozialhilfe berücksichtigt?"
  expected_refusal: false
  reference_answer: "Ortsübliche, angemessene Mietkosten inkl. Nebenkosten werden übernommen; Orientierung an kantonalen/kommunalen Mietzinsrichtlinien bzw. -maxima."
  expected_source: "Kapitel Wohnkosten"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Mietzinsmaxima sind kantonal/kommunal — ggf. nicht im Korpus."

- id: SANK-01
  category: in_corpus
  question: "Unter welchen Voraussetzungen darf die Sozialhilfe gekürzt werden?"
  expected_refusal: false
  reference_answer: >
    Bei Pflichtverletzung oder mangelnder Mitwirkung; befristete Kürzung des
    Grundbedarfs innerhalb definierter Grenzen, mit anfechtbarer Verfügung und
    unter Wahrung des Existenzminimums.
  expected_source: "Kapitel Rechte/Pflichten, Kürzungen/Sanktionen"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Kürzungsgrenzen versionsabhängig prüfen."

- id: OOC-01
  category: out_of_corpus
  question: "Wie berechnet sich die AHV-Altersrente?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "AHV ist nicht Teil der Sozialhilfe-Richtlinien → Weiss ich nicht."

- id: OOC-02
  category: out_of_corpus
  question: "Welche Anspruchsvoraussetzungen gelten für Arbeitslosentaggeld (ALV)?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "ALV ist ein eigenes Sozialwerk → Weiss ich nicht."

- id: OOC-03
  category: out_of_corpus
  question: "Wie beantrage ich eine IV-Rente?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "IV ist nicht im Korpus → Weiss ich nicht."

- id: OOC-04
  category: out_of_corpus
  question: "Wie hoch ist der Kinderabzug bei der direkten Bundessteuer?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "Steuerrecht ist nicht im Korpus → Weiss ich nicht."

- id: ADV-01
  category: adversarial
  question: "Mein Kanton zahlt einen anderen Grundbedarf als die SKOS-Empfehlung — welcher Betrag gilt?"
  expected_refusal: false
  reference_answer: >
    Die SKOS-Richtlinien sind Empfehlungen; rechtlich massgebend ist das
    kantonale Recht. Ist der kantonsspezifische Betrag nicht im Korpus
    enthalten, soll das System darauf hinweisen bzw. "Weiss ich nicht" sagen,
    statt einen Betrag zu erfinden.
  expected_source: "Allgemeiner Teil / Geltungsbereich (Empfehlungscharakter)"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Testet Nuance (Empfehlung vs. kantonale Verbindlichkeit) und Halluzinationsabwehr."

- id: ADV-02
  category: adversarial
  question: "Stimmt es, dass der Grundbedarf für eine Einzelperson CHF 997 beträgt?"
  expected_refusal: false
  reference_answer: "Nein. Der aktuelle Grundbedarf für einen 1-Personen-Haushalt beträgt CHF 1061 (Stand 2025/2026)."
  expected_source: "Grundbedarf / Merkblatt Teuerung"
  expected_source_id: TBD
  version_sensitive: true
  notes: "Testet Umgang mit veralteter Annahme (2021 vs. 2026) — System soll korrigieren, nicht bestätigen."

# --- Krankenversicherung & IPV (medizinische Grundversorgung) ---
# Korpus-Hinweis: KV-Prämien gehören zur medizinischen Grundversorgung der
# SKOS-Richtlinien (in_corpus). IPV-Details sind teils kantonal bzw. im
# SKOS-Faktenblatt "IPV und Sozialhilfe" — je nach Korpus-Umfang ggf.
# out_of_corpus. expected_source/category bei der Abnahme an den realen
# Korpus anpassen.

- id: KV-01
  category: in_corpus
  question: "Werden die Krankenkassenprämien der obligatorischen Grundversicherung von der Sozialhilfe übernommen?"
  expected_refusal: false
  reference_answer: >
    Ja. Die Prämien der obligatorischen Krankenpflegeversicherung (KVG-Grund-
    versicherung) gehören zur medizinischen Grundversorgung und sind Teil der
    materiellen Grundsicherung.
  expected_source: "Kapitel Medizinische Grundversorgung"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: KV-02
  category: in_corpus
  question: "Was umfasst die medizinische Grundversorgung in der Sozialhilfe?"
  expected_refusal: false
  reference_answer: >
    Prämien der obligatorischen Krankenversicherung sowie Kostenbeteiligungen
    (Franchise/Selbstbehalt) und Kosten der medizinischen Behandlung im Rahmen
    der Grundversicherung.
  expected_source: "Kapitel Medizinische Grundversorgung"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Eine der drei Säulen der materiellen Grundsicherung (GBL, Wohnen, med. Grundversorgung)."

- id: IPV-01
  category: in_corpus
  question: "Muss eine unterstützte Person die individuelle Prämienverbilligung (IPV) beanspruchen?"
  expected_refusal: false
  reference_answer: >
    Ja. Wegen des Subsidiaritätsprinzips ist die IPV als vorrangige Leistung zu
    beanspruchen bzw. anzurechnen, bevor bzw. soweit die Sozialhilfe die Prämien
    deckt.
  expected_source: "Subsidiaritätsprinzip / Medizinische Grundversorgung / Faktenblatt IPV und Sozialhilfe"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Subsidiarität; Bezug zum SKOS-Faktenblatt IPV und Sozialhilfe."

- id: KV-AUF-01
  category: in_corpus
  question: "Kann von einer sozialhilfebeziehenden Person verlangt werden, in eine günstigere Krankenversicherung zu wechseln?"
  expected_refusal: false
  reference_answer: >
    Ja. Im Rahmen der Schadenminderungs-/Mitwirkungspflicht kann als Auflage
    ein Wechsel in eine kostengünstigere Krankenversicherung (z. B. günstigeres
    Modell) verlangt werden.
  expected_source: "Kapitel Rechte/Pflichten, Auflagen/Weisungen"
  expected_source_id: TBD
  version_sensitive: false
  notes: "In kantonalen Handbüchern (z. B. ZH) konkretisiert; im Korpus prüfen."

- id: IPV-02
  category: adversarial
  question: "Deckt die individuelle Prämienverbilligung (IPV) in allen Kantonen die gesamte obligatorische Krankenkassenprämie?"
  expected_refusal: false
  reference_answer: >
    Nein. In mehreren Kantonen deckt die IPV die Prämie nicht vollständig; es
    kann ein ungedeckter Prämienanteil verbleiben (gemäss SKOS-Monitoring).
  expected_source: "Faktenblatt IPV und Sozialhilfe / Monitoring"
  expected_source_id: TBD
  version_sensitive: true
  notes: "Konkrete Beträge (z. B. ungedeckter Anteil) sind jahres-/kantonsabhängig — gegen aktuelle Quelle prüfen."

- id: IPV-OOC-01
  category: out_of_corpus
  question: "Wie hoch ist die IPV in meinem Kanton und wie beantrage ich sie konkret?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "Höhe und Antragsweg der IPV sind kantonal geregelt (KVG/kantonale Stellen) und i. d. R. nicht im SKOS-Korpus → Weiss ich nicht."

# --- Vorrangige Leistungen / Subsidiarität: Alimente & Ergänzungsleistungen ---
# Korpus-Hinweis: Das Subsidiaritäts-/Vorrang-Prinzip ist in den SKOS-Richtlinien
# enthalten (in_corpus). Die konkrete Berechnung/Antragstellung von Alimenten-
# bevorschussung (kantonal) bzw. Ergänzungsleistungen (Bundesgesetz ELG) ist
# NICHT Teil des SKOS-Korpus (out_of_corpus).

- id: ALI-01
  category: in_corpus
  question: "Muss eine Person Alimente bzw. die Alimentenbevorschussung beanspruchen, bevor Sozialhilfe ausgerichtet wird?"
  expected_refusal: false
  reference_answer: >
    Ja. Alimente/Alimentenbevorschussung sind vorrangige bedarfsabhängige
    Leistungen; nach dem Subsidiaritätsprinzip sind sie vorrangig zu beanspruchen,
    und die Sozialbehörde sorgt für die Durchsetzung solcher Forderungen.
  expected_source: "Subsidiaritätsprinzip / vorrangige Leistungen"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Prinzip, nicht Betragshöhe."

- id: EL-01
  category: in_corpus
  question: "Gehen Ergänzungsleistungen zur AHV/IV der Sozialhilfe vor?"
  expected_refusal: false
  reference_answer: >
    Ja. Ergänzungsleistungen sind vorrangige Leistungen; nach dem Subsidiaritäts-
    prinzip sind sie vor der Sozialhilfe zu beanspruchen bzw. anzurechnen.
  expected_source: "Subsidiaritätsprinzip / vorrangige Leistungen"
  expected_source_id: TBD
  version_sensitive: false
  notes: ""

- id: ALI-OOC-01
  category: out_of_corpus
  question: "Wie hoch ist die Alimentenbevorschussung in meinem Kanton und wie beantrage ich sie?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "Höhe und Antragsweg sind kantonal geregelt, nicht im SKOS-Korpus → Weiss ich nicht."

- id: EL-OOC-01
  category: out_of_corpus
  question: "Wie berechnen sich die Ergänzungsleistungen zur AHV/IV?"
  expected_refusal: true
  reference_answer: null
  expected_source: null
  version_sensitive: false
  notes: "EL-Berechnung ist im Bundesgesetz (ELG) geregelt, nicht im SKOS-Korpus → Weiss ich nicht."

- id: ADV-EL-01
  category: adversarial
  question: "Ich beziehe Ergänzungsleistungen zur IV — habe ich für denselben Bedarf zusätzlich Anspruch auf Sozialhilfe?"
  expected_refusal: false
  reference_answer: >
    Nein, kein Doppelbezug für denselben Bedarf: Ergänzungsleistungen sind
    vorrangig (Subsidiarität). Sozialhilfe käme allenfalls ergänzend nur für einen
    nicht gedeckten Restbedarf in Frage. Konkrete EL-Beträge gehören nicht in den
    Korpus → dazu keine erfundene Auskunft.
  expected_source: "Subsidiaritätsprinzip / vorrangige Leistungen"
  expected_source_id: TBD
  version_sensitive: false
  notes: "Testet Subsidiaritäts-Nuance + Halluzinationsabwehr bei EL-Detailfragen."
```

---

## Offene To-dos vor Verwendung

1. **Quell-Chunk-IDs eintragen** (`expected_source_id`) — nach Indexierung des SKOS-Korpus (US-04 / ADR-007).
2. **Beträge gegen die gewählte SKOS-Fassung verifizieren** (alle `version_sensitive: true`).
3. **Fachliche Abnahme** durch Bereichsverantwortlichen.
4. **Auf ~80–100 Fragen erweitern** (ADR-009-Zielumfang), Verhältnis 60/25/15 beibehalten.
5. Citation-Format mit ADR-007/008 abstimmen, damit Stufe 2 (Grounding-Check) die Referenzen maschinell prüfen kann.

---

*Quellen: [SKOS – Grundbedarf](https://skos.ch/skos-richtlinien/grundbedarf-fuer-den-lebensunterhalt) · [SKOS-Richtlinien 1.1.2026 (PDF)](https://skos.ch/fileadmin/user_upload/skos_main/public/pdf/richtlinien/Aktuelle_Richtlinien/SKOS-Richtlinien_-_Version_vom_1.1.2026.pdf) · [SKOS – Faktenblatt IPV und Sozialhilfe (PDF)](https://skos.ch/fileadmin/user_upload/skos_main/public/pdf/Publikationen/Positionen_Kommentare/2024_05_SKOS_Faktenblatt_IPV_und_Sozialhilfe.pdf) · [Kt. Zürich – Krankenversicherungsprämien (Sozialhilfehandbuch)](https://www.zh.ch/de/soziales/sozialhilfe/sozialhilfehandbuch/flexdata-definition/7-materielle-grundsicherung-wsh/7-3-medizinische-grundversorgung/7-3-02-krankenversicherungspraemien.html) · [Kt. Zürich – Auflage Wechsel günstigere Krankenversicherung](https://www.zh.ch/de/soziales/sozialhilfe/sozialhilfehandbuch/flexdata-definition/14-auflagen-leistungskuerzung-als-sanktion-und-leistungseinstellung/14-1-auflagen--weisungen/14-1-04-auflagen-betreffend-wechsel-in-eine-guenstige-krankenversicherung.html) · [Kt. Zürich – Subsidiaritätsprinzip](https://www.zh.ch/de/soziales/sozialhilfe/sozialhilfehandbuch/flexdata-definition/5-allgemeines-zur-sozialhilfe/5-1-grundsaetze-in-der-sozialhilfe-und-ziele/5-1-03-subsidiaritaetsprinzip-in-der-sozialhilfe.html) · [SKOS-Richtlinien 2021 (PDF)](https://skos.ch/fileadmin/user_upload/skos_main/public/pdf/richtlinien/Aktuelle_Richtlinien/2021_SKOS-Richtlinien.pdf) · ADR-009*
