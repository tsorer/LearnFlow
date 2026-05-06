# LearnFlow – Kickoff Chat-Verlauf

**Kontext:** CAS Application Development with AI 2026 · BFH Biel
**Modul:** Modul 1 Tag 1 – Projekt-Kickoff (Ilja Rasin)
**Teilnehmer:** Frank Moritz (PO-Rolle) im Sparring mit Claude
**Datum:** 3. Mai 2026

> Hinweis: Wörtlicher Verlauf der Diskussion entlang der Kickoff-Vorlage „Projekt-Kickoff mit AI". Reihenfolge und Inhalte stammen aus dem laufenden Chat. Geringfügige Glättungen möglich (kein wörtliches Transkript-Tool verfügbar).

---

## Turn 1 — Frank

> Kontext: Ich mache einen Kurs für die Entwicklung einer Anwendung mittels KI (also Claude Code). Im Rahmen des Kurses sollen wir den gesamten Entwicklungsprozess durchspielen. Los geht es mit der Ideenfindung.
>
> Rolle: erfahrener PO.
>
> Idee: In der Firma haben wir das Problem, dass neue Mitarbeiter sich schwertun das notwendige Fachwissen aufzubauen. Das wollen wir mit einer neuen Plattform unterstützen. Die Anwendung steht im internen Netz zur Verfügung. Die Bereichsverantwortlichen können Dokumentationen und andere Unterlagen bereitstellen und die Mitarbeiter können damit zum einen Fragen zu bestimmten Themen stellen und zum anderen mittels Quizfragen auch ihr Wissen testen.

## Turn 1 — Claude

Spannende Idee. Eine Plattform, die internes Fachwissen für neue Mitarbeiter zugänglich macht, ist ein klassischer Use Case mit hohem Mehrwert: Onboarding-Zeit verkürzen, Bereichsverantwortliche entlasten, Wissen konservieren.

Bevor wir loslegen: lass mich kurz klären, wo du als PO ansetzen möchtest. Im Ideation-Schritt gibt es typischerweise mehrere Artefakte, die wir erarbeiten könnten – ich möchte sicherstellen, dass wir genau das produzieren, was dein Kurs erwartet bzw. was dir am meisten hilft.

*[Stellte 3 Klärungsfragen via AskUserQuestion: welches Artefakt, welches Format, wie viel Detailtiefe]*

## Turn 2 — Frank (Antworten)

- Format: Erst im Chat diskutieren
- Detailtiefe: Ich gebe dir noch mehr Kontext

## Turn 2 — Claude

Sehr gut – dann sparren wir erstmal im Chat, bevor wir etwas verschriftlichen. Bevor ich gezielte Rückfragen stelle: Schieß einfach mal los mit dem zusätzlichen Kontext. Damit du nichts Wichtiges vergisst, hier die Dimensionen, die für die nächsten Schritte als PO besonders relevant wären:

- **Firma & Branche** – In welcher Branche seid ihr unterwegs, wie groß ist die Firma, und um was für Fachwissen geht es konkret?
- **Zielgruppe „neue Mitarbeiter"** – Berufseinsteiger, Quereinsteiger, erfahrene Fachkräfte? Wie viele kommen pro Jahr/Monat?
- **Bereichsverantwortliche** – Wie viele wären das ungefähr? Sind das Leute, die gerne Inhalte pflegen?
- **Vorhandene Wissensquellen** – Was für Dokumente liegen heute schon vor (Confluence, SharePoint, PDFs, Videos, Wikis)?
- **Constraints** – Internes Netz: heißt das on-prem only? Vorgaben zu KI-Modellen, Datenschutz, Compliance, Sprachen?
- **Erfolgsmessung** – Woran würdet ihr in 6–12 Monaten erkennen, dass die Plattform erfolgreich ist?

Beantworte einfach das, was du weißt oder was im Rahmen des Kurses sinnvoll festzulegen wäre.

---

## Turn 3 — Frank

> Gehen wir nach dem vorgegebenen Muster vor. Diese drei Fragen sollen zuerst geklärt werden:
> 1. Ist die Idee klar genug — oder zu vage?
> 2. Was ist das größte Risiko?
> 3. Wie würdest du die Idee in einem Satz verbessern?

## Turn 3 — Claude

**1. Ist die Idee klar genug — oder zu vage?**

Eher noch zu vage. Die *Funktionen* sind klar (Q&A + Quiz auf hochgeladenen Dokumenten), aber das *Produkt* nicht: Es fehlen Zielgruppen-Schärfung, das konkrete Problem hinter dem Problem (wodurch entsteht die Lernhürde heute?) und ein messbares Ziel. Solange das fehlt, kann man die Idee in zehn Richtungen bauen – und neun davon bringen wenig.

**2. Was ist das größte Risiko?**

Nicht die Technik – die ist mit RAG + LLM heute Standard. Das größte Risiko ist die **Content-Pipeline**: Die Plattform lebt davon, dass Bereichsverantwortliche aktuelle, qualitativ hochwertige Dokumentation einstellen *und* pflegen. Erfahrungsgemäß ist das die ungeliebteste Aufgabe der Welt. Wenn der Content veraltet, halluziniert das System, Mitarbeiter verlieren das Vertrauen, die Plattform stirbt einen leisen Tod.

Sekundärrisiko: **Vertrauen in die KI-Antworten.** Bei Fachwissen sind falsche Antworten teurer als gar keine – Quellenangaben, Confidence-Scores und ein klares „weiß ich nicht" sind Pflicht.

**3. Wie würdest du die Idee in einem Satz verbessern?**

> „Eine interne Lernplattform, die neuen Mitarbeitern bereichsspezifisches Fachwissen über KI-gestützte, **immer quellenbelegte** Antworten und adaptive Quizfragen vermittelt – mit einem **schlanken Redaktions-Workflow, der Bereichsverantwortlichen die Pflege der Inhalte so leicht macht, dass sie tatsächlich stattfindet.**"

Der Kern der Verbesserung: Erfolg hängt nicht an den Lerner-Features, sondern an Quellenbelegung (Vertrauen) und Redaktions-UX (Aktualität).

---

## Turn 4 — Frank

> Die Idee ist noch so vage, weil ich verschiedene Anwendungsbereiche sehe. Zum einen eine generische für den Kurs. Zum anderen zwei verschiedene echte Anwendungsfälle:
> 1. Wir sind Entwickler von Fachanwendungen und müssen um die Fachprozesse umsetzen zu können auch etwas davon verstehen. Konkretes Beispiel: Fachanwendung für Sozialdienste mit Prozessen wie Grundbedarf erfassen, Krankenversicherung, Wohnkosten, aber auch Suchtberatungsprozesse und ähnliches.
> 2. Auch die Sachbearbeiter die später mit der Anwendung arbeiten müssen wissen, wie sie die Anwendung bedienen müssen.
>
> Sollte man es offen lassen oder sich auf einen Anwendungsfall konzentrieren?

## Turn 4 — Claude

Klare PO-Empfehlung: **Konzentrier dich auf einen Anwendungsfall.** Und zwar nicht aus Bequemlichkeit, sondern weil die drei Varianten – obwohl sie technisch gleich aussehen (RAG + Quiz) – als *Produkte* sehr unterschiedlich sind. Wer alles abdecken will, baut am Ende eine Plattform, die für niemanden richtig passt.

| Dimension | Fall 1: Entwickler lernen Fachdomäne | Fall 2: Sachbearbeiter lernen App | Generisch (Kurs) |
|---|---|---|---|
| Zielgruppe | wenige, analytisch, technikaffin | viele, fachlich, prozessorientiert | unklar |
| Content-Art | Gesetze, Fachprozesse, Kundenspezifikationen | Bedienung, Klick-Pfade | beliebig |
| Änderungsfrequenz | mittel (Gesetze, Kundenprozesse) | hoch (jedes Release) | egal |
| Folgen falscher Antworten | falsche Implementierung → fällt im Review/Test auf | falsche Sachbearbeitung → trifft Bürger direkt | hypothetisch |

**Mein Vorschlag: Fall 1 als primärer Use Case.** Drei Gründe:

1. **Lernschleife für dich als PO**: Du bist selbst in der Zielgruppe und kannst dogfooden.
2. **Kleinerer, klarerer Scope**: Wenige Entwickler in einem Bereich, überschaubarer MVP.
3. **Niedrigeres Risiko**: Halluzinationen treffen Entwickler, die im Review gegenchecken können – nicht direkt Klient:innen einer Sozialberatung.

**Strategisch attraktiv:** Wenn ihr es gut baut, ist es eine Vorstufe von Fall 2. Die Architektur ist übertragbar. Das verkaufst du im Kurs als „skalierbare Vision mit fokussiertem MVP".

**Mein Ein-Satz-Vorschlag:**
> „Eine interne Lernplattform, die neue Entwickler:innen bei [Firma] beim Aufbau des fachlichen Domänenwissens unterstützt, das sie zur Umsetzung von Fachanwendungen (z.B. Sozialdienste) brauchen – über quellenbelegte KI-Antworten und adaptive Quizfragen auf Basis der vom jeweiligen Fachbereich kuratierten Dokumentation."

---

## Turn 5 — Frank

> Ich hab die Vorlage angehängt.
> Zielgruppe: neue Mitarbeiter (Entwickler, Requirements-Engineers, Tester)
> Das Problem das wir lösen: Software ist über die Jahre gewachsen und die Infos sind weit gestreut (Confluence, Jira-Tickets, Quell-Code, Workshop-Protokolle). Sehr viele verschiedene Teilbereiche.
> Heute löst man das so: Dokus lesen, andere Mitarbeiter fragen.
>
> Stelle uns 5 kritische Fragen die wir noch nicht beantwortet haben.
> Dann fasse unsere Idee in 3 klaren Sätzen zusammen.

## Turn 5 — Claude

### 5 kritische Fragen, die wir noch nicht beantwortet haben

**1. Pilot-Scope: Womit fangen wir an?**
Welcher *einzelne* Fachbereich oder Domänen-Slice ist der Pilot – und warum genau dieser?

**2. Quellen & Berechtigungen: Was wird angezapft – und wer darf was sehen?**
Spiegeln wir die bestehenden Berechtigungen 1:1 (technisch aufwendig) oder bauen wir einen kuratierten „Lern-Korpus" daneben (organisatorisch aufwendig)?

**3. Inhaltspflege: Wer ist verantwortlich – und ist das realistisch?**
Wer kuratiert, freigibt und aktualisiert Inhalte pro Bereich? Wer prüft auto-generierte Quizfragen?

**4. Vertrauen & Fehler: Was passiert, wenn die KI halluziniert?**
Wie werden Quellen sichtbar belegt? Was zeigt das System, wenn es unsicher ist? Wie meldet ein Nutzer Fehler?

**5. Erfolgsmessung: Woran sehen wir in 6 Monaten, dass es wirkt?**
Was ist die Baseline – wie lange dauert Einarbeitung *heute* messbar?

### 3-Satz-Zusammenfassung

1. Wir bauen eine interne, im Firmennetz betriebene Lernplattform für neue Entwickler:innen, Requirements-Engineers und Tester:innen, die ihnen das fachliche Domänen- und Systemwissen unserer historisch gewachsenen Fachanwendungen (z.B. Sozialdienste) zugänglich macht.

2. Sie stellen Fragen in natürlicher Sprache und erhalten quellenbelegte KI-Antworten aus den vom jeweiligen Fachbereich freigegebenen Inhalten (Confluence, Jira, Workshop-Protokolle, Code) – und können ihr Verständnis mit adaptiven Quizfragen prüfen.

3. Statt Wissen mühsam aus verstreuten Quellen zusammenzusuchen oder erfahrene Kolleg:innen ständig zu unterbrechen, bekommen Neue einen zentralen, immer verfügbaren Lernzugang – und die erfahrenen Kolleg:innen Zeit für die wirklich anspruchsvollen Fragen.

---

## Turn 6 — Frank

> Hier noch die Antworten:
> 1. Den Bereich wo wir eine Unterstützung haben und auch eine ganz gute Datenlage
> 2. Zweite Variante: Wir bauen einen kuratierten „Lern-Korpus" daneben (organisatorisch aufwendig)
> 3. Die Bereiche, die das Tool nutzen wollen müssen auch einen Verantwortlichen bestimmen. Ist eine organisatorische Frage, die wir hier im Projekt nicht klären können. Anhand vom Pilotprojekt lässt sich eventuell der Zeitaufwand bestimmen.
> 4. Es braucht eine Möglichkeit, dass der Benutzer Feedback geben kann. Wie unsichere Antworten angezeigt werden, ist Bestandteil vom Projekt.
> 5. Lässt sich wohl nicht direkt messen. Braucht wohl eine Umfrage unter den Mitarbeitern.
>
> Sind es gute Antworten auf die Fragen?

## Turn 6 — Claude

Ehrliche Einschätzung: **Solide PO-Antworten – mit zwei Stellen, an denen ich nachhaken würde.**

- **Frage 1 – Pilot-Scope: noch zu vage.** „Bereich mit Unterstützung und guter Datenlage" ist ein Auswahl-*Kriterium*, aber kein Ergebnis. Für die Personas und User Stories braucht ihr einen konkreten Bereichsnamen.
- **Frage 2 – Kuratierter Korpus: gute Entscheidung.** Genau der richtige MVP-Move – ein Killer-Risiko (Berechtigungsmodell über vier Quellsysteme) elegant umschifft.
- **Frage 3 – Pflege als Org-Thema: gute Abgrenzung.** Korrekt, das ist kein Software-Problem. Trotzdem im Canvas die *Mindesterwartung* an einen Bereichsverantwortlichen festhalten.
- **Frage 4 – Feedback + Unsicherheit: ok, aber dünn.** Was ich ergänzen würde: **Quellenanzeige ist nicht verhandelbar und gehört nicht ins „klären wir später", sondern als Acceptance Criterion in jede Frage-Antwort-Story.**
- **Frage 5 – nur Umfrage: zu schwach.** Eine reine Mitarbeiterumfrage misst Sympathie, nicht Wirkung. Du brauchst mindestens *eine* harte Zahl.

---

## Turn 7 — Frank

> a) kann ich im Moment noch nicht beantworten.
> b) die ersten beiden Punkte können wir messen. Vorher/nachher-Vergleich ist wieder subjektiv. 4 ist nicht möglich. Bitte nochmal die 3-Satz-Zusammenfassung erstellen und die nächste Phase („skeptischer CTO, 3 größte Risiken") direkt anschließen

## Turn 7 — Claude

### 3-Satz-Zusammenfassung (aktualisiert)

1. Wir bauen eine interne, im Firmennetz betriebene Lernplattform für neue Entwickler:innen, Requirements-Engineers und Tester:innen, die ihnen das fachliche Domänen- und Systemwissen unserer historisch gewachsenen Fachanwendungen (z.B. Sozialdienste) zugänglich macht.

2. Sie stellen Fragen in natürlicher Sprache und erhalten quellenbelegte KI-Antworten aus einem pro Fachbereich **kuratierten Lern-Korpus** (Auszüge aus Confluence, Jira, Workshop-Protokollen, Code) – und können ihr Verständnis mit adaptiven Quizfragen prüfen.

3. Statt Wissen mühsam aus verstreuten Quellen zusammenzusuchen oder erfahrene Kolleg:innen ständig zu unterbrechen, bekommen Neue einen zentralen, immer verfügbaren Lernzugang – und die erfahrenen Kolleg:innen Zeit für die wirklich anspruchsvollen Fragen.

### Skeptischer CTO – Pitch-Reaktion

Drei Dinge, die ich **sofort hinterfrage**:
1. **Warum baut ihr das selbst?** Atlassian Rovo, Glean, Microsoft Copilot, Onyx, Danswer machen das alle.
2. **Wer ist euer Pilotkunde?** „Der Bereich, der mitmacht und gute Daten hat" ist kein Kunde, das ist ein Wunsch.
3. **„Wir messen Erfolg über Nutzungszahlen und Umfrage" ist mir zu wenig.** Nutzung beweist Nutzung, nicht Wirkung.

### Die drei größten Risiken

**Risiko 1 – Content Rot: Die Plattform stirbt an veralteten Inhalten.**
*Wahrscheinlichkeit: hoch. Schaden: Totalverlust.*
*Plan dagegen:* Pflege-Verantwortung schriftlich vom Bereichsleiter unterschreiben lassen. Quartalsweiser Stale-Content-Report. Datum der letzten Validierung sichtbar an jeder Antwort.

**Risiko 2 – Falsche Antworten in einer Fachdomäne, die Anfänger nicht prüfen können.**
*Wahrscheinlichkeit: mittel. Schaden: hoch.*
*Plan dagegen:* Quellenbeleg als harte Acceptance Criterion. „Weiß ich nicht"-Pfad explizit trainieren. Feedback-Mechanik mit kurzem Reaktionsweg.

**Risiko 3 – Build statt Buy: Ihr investiert in eine Lösung, die in zwei Jahren als Standardfunktion eures Confluence-Abos kommt.**
*Wahrscheinlichkeit: hoch. Schaden: verlorene Investition.*
*Plan dagegen:* Vor Projektstart Build-vs-Buy-Analyse. Klare Differenzierung definieren. Architektur mit ersetzbaren Komponenten.

---

## Turn 8 — Frank

> OK

## Turn 8 — Claude (Phase 02 Personas)

### Persona 1 – Lara Fischer, 26, Junior Software Engineer
- **Hintergrund:** FH-Abschluss Informatik, 6 Wochen im Unternehmen, erstes „richtiges" Projekt nach Praktikum.
- **Hauptproblem:** Code zu Fachprozessen schreiben, die sie nicht versteht.
- **Frustriert:** Confluence-Friedhof, Jira erklärt nur das Was nicht das Warum, traut sich nicht dieselbe Frage zum dritten Mal.
- **Ziel:** Innerhalb von 3 Monaten eigene Stories ohne ständige Rückfrage abschließen können.
- **Was sie abhält:** Falsche Antworten, langsamer als Slack, Privacy-Sorge, fehlende Quellen.

### Persona 2 – Stefan Brunner, 51, Senior BA & Bereichsverantwortlicher Sozialdienste
- **Hintergrund:** 18 Jahre im Unternehmen, wandelndes Lexikon, pflegt Confluence selten.
- **Hauptproblem:** Wird täglich 5–8 Mal von Juniors zu denselben Themen unterbrochen.
- **Frustriert:** Dieselben Fragen, Doku-Schreiben kostet Stunden, Pflege steht in keiner Stellenbeschreibung.
- **Ziel:** Wissen konservieren, weniger unterbrochen werden, vor Pension Wissen sichern.
- **Was ihn abhält:** Pflegeaufwand zu hoch, Tool gibt unter seinem Namen falsche Antworten, keine Anerkennung, Sorge sich wegzurationalisieren.

### Vergessene Stakeholder
HR/Personalentwicklung, Datenschutzbeauftragte:r und IT-Security, Betriebsrat, Geschäftsleitung, Schulungs-/Trainingsabteilung, erfahrene Kolleg:innen ohne Pflegerolle.

### Mögliche Gegner
Bereichsverantwortliche, die Wissen als Machtposition sehen. Trainings-/Schulungsabteilung. Datenschutzbeauftragte:r (kein Gegner aus Prinzip, aber Bremser). Betriebsrat (berechtigt). KI-Skeptiker:innen.

### Profitieren / Verlieren
**Profitieren:** Lara, erfahrene Kolleg:innen ohne Pflegerolle, Geschäftsleitung, Kund:innen indirekt.
**Verlieren:** Bereichsverantwortliche kurzfristig, Wissens-Gatekeeper, externe Trainer:innen.

---

## Turn 9 — Frank

> Personas sind super. Bitte weiter.

## Turn 9 — Claude (Phase 03 User Stories)

*[Erstellte 8 User Stories in MoSCoW-Priorisierung mit jeweils Acceptance Criteria im Given/When/Then-Format. Stories: 1 Q&A mit Quellen, 2 Korpus aufnehmen, 3 Feedback, 4 Unsichere Antworten markieren, 5 Stale-Content, 6 Quiz absolvieren, 7 Wissens-Lücken, 8 Persönlicher Fortschritt (Won't).]*

*[Anschließend kritische Review:]*
- Welche zu vage? (4: „2 unabhängige Quellen" Schwelle, 6: was ist „Bereich"?, 7: was ist Cluster?)
- Welche AC nicht testbar? (1: „relevante Stelle", 2: „5 Min" ohne Größenangabe)
- Was vergessen? (Authentifizierung, Admin-Rolle, Quiz-Freigabe, Folgefragen, kaputte Quellen, Edge Cases, Error Cases)
- Welche zuerst bauen? (Story 1 als Walking Skeleton, Korpus initial per Skript)

---

## Turn 10 — Frank

> 4.) AC2: Wieso zwei unabhängige Quellen?
> Anhand von deinen eigenen Kritikpunkten, wie könnte man die 8 UserStories verbessern?

## Turn 10 — Claude

**Zur AC2-Frage:** Ehrliche Antwort: Schwacher Platzhalter von mir. Ich habe eine RAG-Faustregel benutzt, aber sie hält der Prüfung nicht stand: Eine einzelne autoritative aktuelle Quelle ist oft vertrauenswürdiger als zwei redundante. Manche Fragen haben legitim nur eine Quelle. Das Kriterium produziert False Positives.

**Besseres Kriterium:** Konfidenz aus messbaren Signalen ableiten – Retrieval-Similarity-Score unter Schwellwert oder Self-Check-Schritt des Modells.

*[Anschließend Verbesserungen aller 8 Stories: präziser machen, Schwellwerte definieren, Error Cases ergänzen, fehlende Stories hinzufügen (Auth, Admin, Quiz-Freigabe, Folgefragen, kaputte Quellen). Plus drei strukturelle Punkte: Stories teilweise zu groß, NFRs fehlen, fehlende Stories brauchen Slots im Backlog.]*

---

## Turn 11 — Frank

> Bitte die User-Stories nochmal komplett schreiben, damit ich sie leichter ins Dokument einfügen kann. Danach gleich Phase 4 machen.

## Turn 11 — Claude

*[Lieferte komplette ausformulierte 11 User Stories: 1 Q&A mit Quellen [MUST], 2 Korpus aufnehmen [MUST], 3 Feedback [MUST], 4 Unsichere Antworten [MUST], 5 Stale-Content [SHOULD], 6a Quiz absolvieren [SHOULD], 6b Quiz-Freigabe [SHOULD NEU], 7 Wissens-Lücken [COULD], 8 Authentifizierung [MUST NEU], 9 Bereichsverwaltung [MUST NEU], 10 Folgefragen [SHOULD NEU], 11 Kaputte Quellen [SHOULD NEU]. Empfehlung für 8-Slot-Vorlage: 1, 2, 3, 4, 8, 9, 5, 6a.]*

*[Phase 04 Projekt-Canvas:]*
- 📌 Projektname: LearnFlow
- 🎯 Was wir bauen: Lernplattform-Satz
- 👥 Zielgruppe: Lara + Stefan
- 🔥 Problem: verstreute Quellen, veraltete Doku, unterbrochene Kollegen
- ✅ Must-have MVP Top 3: Story 1, 4, 2
- ⚠️ Größtes Risiko: Content Rot + 4-teiliger Plan
- 🤖 Wo AI: LLM-Antworten, Embeddings, Self-Check, Quiz-Generierung. Bewusst KEIN AI: Auth, Pflege, Bereichszuordnung
- 📅 Nächste Schritte: 6 Punkte

---

## Turn 12 — Frank

> Ich brauche eine Präsentation (5 Minuten). Dort sollen die 5 wichtigsten Punkte angesprochen werden. Vorher aber noch die alles entscheidende Frage: Ist es mit 3 Personen bis zum 30. September umsetzbar? (Wir brauchen nicht zwingend eine lauffähige Anwendung)

## Turn 12 — Claude

**Machbarkeit: Ja – mit klarer Scope-Disziplin.**

- Zeitfenster: 21 Wochen / 5 Monate
- Team: 3 Personen, 8–16 h/Woche/Person → ~500–1.000 Personenstunden
- Geschätzter Aufwand für Walking-Skeleton-Prototyp mit 4–5 Stories: ~520 h
- Bedingungen: Tech-Stack in Woche 1 fixiert; Pilot-Bereich + ~50 Dokumente bis Woche 2; Strenge Scope-Disziplin

*[Anschließend Erstellung 5-Minuten-Pitch-Deck als PowerPoint mit 6 Folien: Title + Idee + Top-3-Stories + Risiko/Plan + KI-Einsatz + Was offen ist.]*

[→ LearnFlow_Pitch.pptx](computer://D:\Projects\ADAI\LearnFlow\LeanFlow/LearnFlow_Pitch.pptx)

---

## Turn 13 — Frank

> Exportiere bitte auch den gesamten Verlauf für Dokuzwecke

## Turn 13 — Claude

*[Erstellte zunächst eine strukturierte Word-Doku als Zusammenfassung der Diskussion mit allen Phasen, Personas, Stories, Canvas, Machbarkeit und Anhang.]*

[→ LearnFlow_Kickoff_Doku.docx](computer://D:\Projects\ADAI\LearnFlow\LeanFlow/LearnFlow_Kickoff_Doku.docx)

---

## Turn 14 — Frank

> Die Doku ist auch gut, ich meinte aber diesen gesamten Chat-Verlauf hier. Wie sehe der Plan aus, wenn man Ferien mitberücksichtigt und 15 Wochen und 8h pro Person und Woche möglich sind.

## Turn 14 — Claude

*[Erstellung dieses Chat-Verlaufs als Markdown + neuer Plan unter den realistischen Constraints. Siehe Begleitdokument LearnFlow_Plan_15Wochen.md.]*

---

## Artefakte aus diesem Kickoff

| Artefakt | Pfad |
|---|---|
| Pitch-Deck (5 Min) | `LearnFlow_Pitch.pptx` |
| Strukturierte Doku | `LearnFlow_Kickoff_Doku.docx` |
| Chat-Verlauf (dieses Dokument) | `LearnFlow_Chatverlauf.md` |
| Realistischer Plan (15 W) | `LearnFlow_Plan_15Wochen.md` |

*Ende des Verlaufs.*
