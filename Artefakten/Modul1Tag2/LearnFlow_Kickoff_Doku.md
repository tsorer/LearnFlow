**LearnFlow**

KI-gestützte Lernplattform für die fachliche Einarbeitung

  **Kontext**   CAS Application Development with AI 2026 · BFH Biel
  ------------- ------------------------------------------------------------------------------
  **Modul**     Modul 1 Tag 1 -- Projekt-Kickoff (Ilja Rasin)
  **Autor**     Frank Moritz
  **Datum**     3\. Mai 2026
  **Methode**   Kickoff-Vorlage durchgespielt mit Claude als PO-Sparring-Partner
  **Inhalt**    Phasen 00--04 inkl. überarbeiteter User Stories, Risiko-Analyse, Machbarkeit

*Dieses Dokument ist eine Zusammenfassung der Diskussion entlang der Vorlage „Projekt-Kickoff mit AI". Es enthält die geschärfte Idee, die kritischen Fragen und Antworten, die Personas, alle 11 erarbeiteten User Stories (8 davon im MVP), den Projekt-Canvas, eine Risiko- und Machbarkeitsanalyse sowie das Pitch-Deck als Begleit-Artefakt.*

**Inhalt**
==========

Phase 00 · Projektidee finden und schärfen 3

Phase 01 · Idee schärfen mit Claude (5 kritische Fragen + 3-Satz-Idee) 3

Phase 01 · Skeptischer CTO -- die 3 grössten Risiken 5

Phase 02 · Stakeholder und Personas 6

Phase 03 · User Stories (11 Stories mit MoSCoW + AC) 8

Phase 04 · Projekt-Canvas 13

Machbarkeits-Analyse: 3 Personen, bis 30. September 14

Anhang: Entscheidungs-Log 15

**Phase 00 · Projektidee finden und schärfen**
==============================================

**Ausgangslage**
----------------

In der Firma haben neue Mitarbeiter:innen Schwierigkeiten, das nötige Fachwissen aufzubauen. Eine interne Plattform soll dabei unterstützen: Bereichsverantwortliche stellen Dokumentationen bereit, Mitarbeiter:innen können dazu Fragen stellen und ihr Wissen über Quizfragen testen. Die Anwendung läuft im internen Netz.

**Ehrliche Frage und Diskussion**
---------------------------------

Drei mögliche Anwendungsbereiche standen zur Auswahl:

-   Generischer Anwendungsfall für den Kurs.

-   Reale Variante 1: Entwickler:innen lernen die Fachdomäne, um Fachanwendungen (z.B. Sozialdienste mit Prozessen wie Grundbedarf, Krankenversicherung, Wohnkosten, Suchtberatung) korrekt umsetzen zu können.

-   Reale Variante 2: Sachbearbeiter:innen, die später die Anwendung bedienen müssen, lernen die Anwendung.

**Entscheidung**
----------------

Fokus auf Variante 1 (Entwickler:innen lernen Fachdomäne). Begründung:

1.  **Eigene Nutzung:** Lernschleife für Frank als PO -- ist selbst in der Zielgruppe und kann das Produkt täglich dogfooden.

2.  **Scope:** Kleinerer, klarerer Scope -- wenige Entwickler:innen in einem Bereich, überschaubarer MVP, schnelle Validierung.

3.  **Risiko:** Halluzinationen treffen Entwickler:innen, die im Code-Review oder Sparring mit BA gegenchecken können -- nicht direkt Klient:innen einer Sozialberatung.

4.  **Strategisch:** Die Architektur ist später auf Variante 2 übertragbar -- fokussierter MVP mit skalierbarer Vision.

**Phase 01 · Idee schärfen mit Claude**
=======================================

**Ausgangs-Eingaben (gemäss Vorlage)**
--------------------------------------

  **Wir wollen bauen**       Eine interne Lernplattform für Wissensaufbau in der Firma.
  -------------------------- ------------------------------------------------------------------------------------------------------------------------------------------
  **Zielgruppe**             Neue Mitarbeiter:innen (Entwickler:innen, Requirements-Engineers, Tester:innen)
  **Problem**                Software ist über Jahre gewachsen, Infos sind weit gestreut (Confluence, Jira, Quellcode, Workshop-Protokolle); sehr viele Teilbereiche.
  **Heute löst man es so**   Dokumentation lesen, andere Mitarbeiter:innen fragen.

**Claudes 5 kritische Fragen**
------------------------------

**Frage 1: Pilot-Scope: Womit fangen wir an?**

Welcher einzelne Fachbereich oder Domänen-Slice ist der Pilot -- und warum?

**Frage 2: Quellen und Berechtigungen**

Welche Systeme zapfen wir an, und wie gehen wir mit unterschiedlichen Zugriffsrechten und veralteten Inhalten um?

**Frage 3: Inhaltspflege**

Wer ist verantwortlich, wer kuratiert, freigibt und aktualisiert? Wieviel Aufwand pro Monat ist realistisch?

**Frage 4: Vertrauen und Fehler**

Was passiert, wenn die KI etwas Falsches sagt? Wie werden Quellen belegt? Wie erkennt das System Unsicherheit?

**Frage 5: Erfolgsmessung**

Woran erkennen wir nach 3/6/12 Monaten, dass das Tool wirkt? Gibt es eine Baseline?

**Franks Antworten**
--------------------

**Pilot-Scope:** Ein Bereich mit interner Unterstützung und guter Datenlage -- konkreter Bereich wird zu einem späteren Zeitpunkt benannt.

**Quellen und Berechtigungen:** Wir bauen einen kuratierten Lern-Korpus parallel zu den bestehenden Systemen (organisatorisch aufwendiger, aber technisch sauber abgegrenzt -- vermeidet Berechtigungsmodell über vier Quellsysteme).

**Inhaltspflege:** Bereiche, die das Tool nutzen wollen, müssen einen Verantwortlichen bestimmen. Das ist eine organisatorische Frage, die im Projekt nicht geklärt wird. Anhand des Pilotprojekts lässt sich der Zeitaufwand bestimmen.

**Vertrauen und Fehler:** Es braucht eine Möglichkeit für Nutzer-Feedback. Wie unsichere Antworten konkret angezeigt werden, ist Bestandteil des Projekts.

**Erfolgsmessung:** Direkt messbar wahrscheinlich nicht -- aber Nutzungszahlen pro Mitarbeiter:in und Anteil positiver Feedbacks sind quantitativ erfassbar; ergänzend dazu eine Mitarbeiter-Umfrage.

**Bewertung dieser Antworten (Sparring durch Claude)**
------------------------------------------------------

Solide PO-Antworten -- mit zwei Stellen, an denen nachgebessert werden sollte. Die Antworten 1 (Pilot-Scope) und 5 (Erfolgsmessung) sind noch zu weich.

-   **Frage 1:** Pilot-Scope ist noch ein Auswahl-Kriterium, kein Ergebnis. Für Personas und User Stories braucht es einen konkret benannten Bereich.

-   **Frage 2:** Kuratierter Korpus ist die richtige MVP-Entscheidung -- sollte als bewusste Scope-Entscheidung im Canvas dokumentiert werden.

-   **Frage 3:** Org-Thema korrekt abgegrenzt. Trotzdem im Canvas Mindesterwartung an Bereichsverantwortliche festhalten (Person nominiert, \~2h/Monat, Pflege und Freigabe-Verantwortung).

-   **Frage 4:** Feedback ist Pflicht -- aber Quellenanzeige ist nicht verhandelbar und gehört als Acceptance Criterion in jede Q&A-Story, nicht ins Später-Backlog.

-   **Frage 5:** Reine Umfrage misst Sympathie, nicht Wirkung. Eine quantitative Kennzahl ist Pflicht. Frank hat ergänzt: Anzahl Anfragen pro Mitarbeiter:in und Anteil positiver Feedbacks lassen sich direkt messen.

**3-Satz-Zusammenfassung der Idee (final)**
-------------------------------------------

+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **LearnFlow -- Idee in drei Sätzen**                                                                                                                                                                                                                                            |
|                                                                                                                                                                                                                                                                                 |
| 1\. Wir bauen eine interne, im Firmennetz betriebene Lernplattform für neue Entwickler:innen, Requirements-Engineers und Tester:innen, die ihnen das fachliche Domänen- und Systemwissen unserer historisch gewachsenen Fachanwendungen (z.B. Sozialdienste) zugänglich macht.\ |
| \                                                                                                                                                                                                                                                                               |
| 2. Sie stellen Fragen in natürlicher Sprache und erhalten quellenbelegte KI-Antworten aus einem pro Fachbereich kuratierten Lern-Korpus (Auszüge aus Confluence, Jira, Workshop-Protokollen, Code) -- und können ihr Verständnis mit adaptiven Quizfragen prüfen.\              |
| \                                                                                                                                                                                                                                                                               |
| 3. Statt Wissen mühsam aus verstreuten Quellen zusammenzusuchen oder erfahrene Kolleg:innen ständig zu unterbrechen, bekommen Neue einen zentralen, immer verfügbaren Lernzugang -- und die erfahrenen Kolleg:innen Zeit für die wirklich anspruchsvollen Fragen.               |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Phase 01 · Skeptischer CTO -- die 3 grössten Risiken**
========================================================

Vorbemerkung des CTO: drei Punkte, die er sofort hinterfragt:

-   **Build vs. Buy:** Atlassian Rovo, Glean, Microsoft Copilot bieten RAG-auf-Confluence/Jira als Standardprodukt. Was rechtfertigt eine eigene Entwicklung?

-   **Pilotkunde:** Der Bereich, der mitmacht, ist kein Kunde, sondern ein Wunsch. Vor Projektstart muss ein Bereichsleiter unterschreiben.

-   **Erfolgsmessung:** Nutzungszahlen + Umfrage messen Sympathie und Adoption, aber nicht Wirkung. Eine Aussage zu schneller-produktiv fehlt.

### **Risiko 1 -- Content Rot**

**Wahrscheinlichkeit:** hoch **Schaden:** Totalverlust

Die ganze Architektur lebt davon, dass jemand pro Bereich aktiv kuratiert. Genau dieser Teil wurde bewusst aus dem Projekt herausdefiniert. Innerhalb von sechs Monaten nach Launch wird eine Antwort auf veralteter Confluence-Seite basieren, das wird im Team rumgehen, das Vertrauen ist weg.

**Plan dagegen:**

-   Pflege-Verantwortung schriftlich vom Bereichsleiter unterschreiben lassen.

-   Quartalsweiser Stale-Content-Report automatisiert.

-   Datum der letzten Validierung sichtbar an jeder Antwort.

### **Risiko 2 -- Falsche Antworten in einer Fachdomäne**

**Wahrscheinlichkeit:** mittel **Schaden:** hoch (Vertrauensverlust + falsche Implementierungen, die durchrutschen)

Sozialdienst-Recht ist nicht trivial. Berufseinsteiger:innen haben keine Chance, plausibel-klingenden Unsinn zur SKOS-Berechnung zu erkennen -- im Gegensatz zu Senior-Kolleg:innen. Genau für diese Zielgruppe ist Halluzination am gefährlichsten.

**Plan dagegen:**

-   Quellenbeleg als harte Acceptance Criterion in jeder Antwort.

-   Weiss-ich-nicht-Pfad explizit trainieren und testen.

-   Feedback-Mechanik mit kurzem Reaktionsweg an die Bereichsverantwortlichen.

### **Risiko 3 -- Build statt Buy**

**Wahrscheinlichkeit:** hoch **Schaden:** verlorene Investition

Atlassian, Microsoft & Co. liefern RAG-auf-eigene-Daten zunehmend out-of-the-box. Eine Eigenentwicklung muss sich gegen ein bewegliches Ziel verteidigen.

**Plan dagegen:**

-   Vor Projektstart eine ehrliche Build-vs-Buy-Analyse mit konkreten Tools und Preisen.

-   Klare Differenzierung definieren (z.B. das adaptive Quiz mit Bereichs-Freigabe).

-   Architektur mit ersetzbaren Komponenten -- LLM und Vektor-DB tauschbar.

**Phase 02 · Stakeholder und Personas**
=======================================

**Persona 1 -- Lara Fischer, 26, Junior Software Engineer**
-----------------------------------------------------------

**Hintergrund:** FH-Abschluss Informatik, seit 6 Wochen im Unternehmen, erstes richtiges Projekt nach Praktikum. Eingeteilt im Sozialdienste-Modul, Domäne neu für sie.

**Hauptproblem (das wir lösen):** Sie muss Code zu Fachprozessen schreiben, die sie nicht versteht (Grundbedarf, KV-Berechnung, Wohnkosten) -- findet das nötige Wissen aber nicht selbst zusammen.

**Was frustriert sie heute:** Confluence ist ein Friedhof. Jira erklärt das Was, nicht das Warum. Sie traut sich nicht, dieselbe Frage zum dritten Mal zu stellen. Senior-Erklärungen sind 20 Minuten lang, sie versteht 5 davon und fragt nicht nach. Oft weiss sie nicht mal, welche Frage die richtige wäre.

**Ihr Ziel:** In den ersten drei Monaten so weit kommen, dass sie eigene Stories ohne ständige Rückfrage abschliessen kann.

**Was sie abhalten könnte:** Antworten, die offensichtlich falsch oder nichtssagend sind. Tool langsamer als ein Slack-Ping. Privacy-Sorge, dass jemand mitliest welche dummen Fragen sie stellt. Antworten ohne Quelle.

**Persona 2 -- Stefan Brunner, 51, Senior BA und Bereichsverantwortlicher**
---------------------------------------------------------------------------

**Hintergrund:** 18 Jahre im Unternehmen, davon 12 im Sozialdienste-Bereich. Wandelndes Lexikon. Pflegt Confluence wenn Zeit da ist -- also selten.

**Hauptproblem (das wir lösen):** Wird täglich 5--8 Mal von Junior:innen zu denselben Themen unterbrochen. Sein Wissen bleibt in seinem Kopf.

**Was frustriert ihn heute:** Dieselben Fragen immer wieder. Doku schreiben kostet Stunden, niemand liest sie. Wenn Doku falsch interpretiert wird, ist er schuld. Pflege steht in keiner Stellenbeschreibung.

**Sein Ziel:** Wissen so konservieren, dass er weniger unterbrochen wird und in fünf Jahren vor der Pensionierung ein gutes Gewissen haben kann, dass das Wissen nicht mit ihm geht.

**Was ihn abhalten könnte:** Pflegeaufwand höher als versprochen. Tool gibt unter seinem Bereichsnamen falsche Antworten -- sein Ruf hängt mit dran. Quiz-Fragen auto-generiert aber fachlich Quatsch. Keine Anerkennung. Sorge, sich wegzurationalisieren.

**Vergessene Stakeholder**
--------------------------

-   HR/Personalentwicklung -- besitzen den Onboarding-Prozess.

-   Datenschutzbeauftragte:r und IT-Security -- kritischer Türsteher für Korpus-Inhalte.

-   Betriebsrat -- sobald Quiz-Ergebnisse oder Nutzungsdaten existieren, kann das als Mitarbeiterbewertung interpretiert werden.

-   Geschäftsleitung -- Sponsoren, brauchen Reporting (siehe Erfolgsmessung).

-   Schulungs-/Trainingsabteilung -- fühlt sich potenziell teilersetzt.

-   Erfahrene Kolleg:innen ohne Pflegerolle -- profitieren, tragen aber nichts bei (Trittbrettfahrer-Dynamik).

**Mögliche Gegner**
-------------------

-   Bereichsverantwortliche, die ihr Wissen als Machtposition sehen -- werden subtil sabotieren.

-   Trainings-/Schulungsabteilung -- sieht Geschäftsmodell tangiert.

-   Datenschutzbeauftragte:r -- kein Gegner aus Prinzip, aber kann das Projekt bremsen.

-   Betriebsrat -- berechtigte Wachsamkeit bei Nutzungsdaten und Quiz-Scores.

-   KI-Skeptiker:innen im Management -- halluziniert doch nur als Pauschalkritik.

**Wer profitiert / wer verliert**
---------------------------------

**Profitieren:**

Neue Mitarbeiter:innen (Lara), erfahrene Kolleg:innen ohne Pflegerolle, Geschäftsleitung (kürzere Time-to-Productivity), Kund:innen indirekt.

**Verlieren:**

Bereichsverantwortliche kurzfristig (zusätzlicher Pflegeaufwand bei unklarem persönlichen Mehrwert -- kritisch), Wissens-Gatekeeper (informelle Macht), externe Trainer:innen (weniger Aufträge).

**Phase 03 · User Stories**
===========================

*Insgesamt 11 Stories nach kritischer Review und Verfeinerung. Alle Acceptance Criteria im Given/When/Then-Format. Empfehlung für die 8-Slot-Vorlage des Kurses: Stories 1, 2, 3, 4, 8, 9, 5, 6a.*

+-------------+-------------------------------------------------------+
| **Story 1** | **Frage stellen und quellenbelegte Antwort bekommen** |
|             |                                                       |
|             | **MUST**                                              |
+-------------+-------------------------------------------------------+

> Als **Lara** möchte ich eine Frage in natürlicher Sprache stellen und eine quellenbelegte Antwort bekommen, damit ich Fachprozesse verstehen kann, ohne erfahrene Kollegen zu unterbrechen.

**Acceptance Criteria**

> **AC1: Given** ich habe eine Frage zu meinem Bereich **When** ich sie im Eingabefeld absende **Then** bekomme ich innerhalb von 10 Sekunden eine Antwort mit mindestens einer Quellenangabe (Dokumenttitel + Verweis).
>
> **AC2: Given** die Antwort verweist auf eine Quelle **When** ich auf die Quellenangabe klicke **Then** öffnet sich die Originalquelle und der belegende Abschnitt ist visuell hervorgehoben (Highlight + automatisches Scrollen).
>
> **AC3: Given** der LLM- oder Retrieval-Service ist nicht erreichbar **When** ich eine Frage absende **Then** erhalte ich eine klare Fehlermeldung Service vorübergehend nicht verfügbar -- keine erfundene Antwort.

+-------------+------------------------------------------+
| **Story 2** | **Inhalte in den Lern-Korpus aufnehmen** |
|             |                                          |
|             | **MUST**                                 |
+-------------+------------------------------------------+

> Als **Stefan** möchte ich Dokumente und Texte in den Lern-Korpus meines Bereichs aufnehmen, damit das System auf aktuelle, von mir freigegebene Inhalte zugreifen kann.

**Acceptance Criteria**

> **AC1: Given** ich lade ein Dokument bis 50 Seiten / 10 MB in einem unterstützten Format (PDF, Markdown, DOCX, Confluence-Export) hoch **When** die Verarbeitung startet **Then** ist es nach maximal 5 Minuten als Quelle verfügbar; bei grösseren Dokumenten zeigt das System eine Fortschrittsanzeige und bestätigt spätestens nach 30 Minuten.
>
> **AC2: Given** der Verarbeitungsprozess endet **When** ich das Dashboard öffne **Then** sehe ich Status (erfolgreich/Fehler), Anzahl extrahierter Abschnitte sowie das Aufnahmedatum.
>
> **AC3: Given** das Format wird nicht unterstützt oder das Dokument ist beschädigt **When** ich es hochlade **Then** sehe ich sofort eine spezifische Fehlermeldung mit Hinweis auf akzeptierte Formate.

+-------------+---------------------------------+
| **Story 3** | **Feedback zu Antworten geben** |
|             |                                 |
|             | **MUST**                        |
+-------------+---------------------------------+

> Als **Lara** möchte ich jede Antwort als hilfreich oder nicht hilfreich markieren und einen Grund angeben, damit unklare oder falsche Antworten korrigiert werden können.

**Acceptance Criteria**

> **AC1: Given** mir wurde eine Antwort angezeigt **When** ich auf Daumen-runter klicke **Then** werde ich nach einer strukturierten Kategorie gefragt (faktisch falsch / unvollständig / veraltet / unverständlich / Quelle stimmt nicht) und kann optional Freitext ergänzen.
>
> **AC2: Given** ich habe Feedback gegeben **When** es gespeichert wurde **Then** erhalte ich eine Bestätigung Danke, dein Feedback wurde an die Bereichsverantwortliche:n weitergeleitet und es erscheint im Bereichs-Dashboard.

+-------------+---------------------------------------+
| **Story 4** | **Unsichere Antworten klar erkennen** |
|             |                                       |
|             | **MUST**                              |
+-------------+---------------------------------------+

> Als **Lara** möchte ich klar erkennen, wenn das System sich seiner Antwort nicht sicher ist, damit ich keinen halluzinierten Inhalten vertraue.

**Acceptance Criteria**

> **AC1: Given** die maximale Retrieval-Similarity der gefundenen Chunks liegt unter dem konfigurierten Schwellwert (zu Projektbeginn empirisch zu kalibrieren) **When** das System antworten würde **Then** antwortet es nicht inhaltlich, sondern mit Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden und schlägt eine Bereichsverantwortliche:n vor.
>
> **AC2: Given** das Modell führt nach der Generierung einen Self-Check durch (Ist die Antwort vollständig aus den gelieferten Quellen belegbar?) **When** das Ergebnis teilweise oder nein ist **Then** wird die Antwort sichtbar als Eingeschränkt belegt markiert und der nicht-belegte Teil hervorgehoben.
>
> **AC3: Given** eine vordefinierte Liste von Out-of-Corpus-Testfragen existiert **When** diese gestellt werden **Then** gibt das System in mindestens 90 % der Fälle ein Weiss ich nicht zurück.

+-------------+--------------------------------------------------+
| **Story 5** | **Veraltete Inhalte erkennen und re-validieren** |
|             |                                                  |
|             | **SHOULD**                                       |
+-------------+--------------------------------------------------+

> Als **Stefan** möchte ich eine Übersicht über veraltete oder lange nicht validierte Inhalte sehen und sie aktiv prüfen können, damit der Korpus aktuell bleibt.

**Acceptance Criteria**

> **AC1: Given** ich öffne das Bereichs-Dashboard **When** in meinem Bereich Dokumente älter als 6 Monate ohne erneute Validierung existieren **Then** werden sie mir in einer sortierten Liste mit Alter und letztem Validierungsdatum angezeigt.
>
> **AC2: Given** ich öffne einen Eintrag aus der Stale-Liste **When** ich auf Validieren klicke **Then** werde ich gefragt, ob der Inhalt geprüft und weiterhin aktuell ist (Ja / Nein, ersetzt durch \... / Nein, entfernen).
>
> **AC3: Given** in meinem Bereich werden Inhalte stale **When** die monatliche Stichtag-Prüfung läuft **Then** erhalte ich eine zusammenfassende Benachrichtigung per E-Mail oder interner Inbox.

+--------------+--------------------------------+
| **Story 6a** | **Wissen mit Quiz überprüfen** |
|              |                                |
|              | **SHOULD**                     |
+--------------+--------------------------------+

> Als **Lara** möchte ich zu einem Bereich ein kurzes Quiz absolvieren, damit ich überprüfen kann, ob ich das Gelesene wirklich verstanden habe.

**Acceptance Criteria**

> **AC1: Given** ich wähle einen Bereich **When** ich auf Quiz-starten klicke **Then** bekomme ich 5 Multiple-Choice-Fragen aus dem Pool freigegebener Quizfragen dieses Bereichs -- jede mit hinterlegter Quelle für die korrekte Antwort.
>
> **AC2: Given** ich habe alle Fragen beantwortet **When** ich das Quiz abschliesse **Then** sehe ich pro Frage richtig/falsch, die korrekte Antwort mit Erklärung sowie den direkten Link zur belegenden Quelle.

+--------------+-------------------------------------------------------+
| **Story 6b** | **Auto-generierte Quizfragen reviewen und freigeben** |
|              |                                                       |
|              | **SHOULD**                                            |
+--------------+-------------------------------------------------------+

> Als **Stefan** möchte ich auto-generierte Quizfragen vor Veröffentlichung reviewen und freigeben können, damit keine fachlich falschen Fragen unter meinem Bereichsnamen verbreitet werden.

**Acceptance Criteria**

> **AC1: Given** das System hat aus Korpus-Inhalten neue Quizfragen generiert **When** ich meine Review-Inbox öffne **Then** sehe ich jede Frage mit Antwortoptionen, markierter korrekter Antwort und der Quellen-Passage, aus der sie generiert wurde.
>
> **AC2: Given** ich prüfe eine Frage **When** ich auf Freigeben / Bearbeiten / Verwerfen klicke **Then** wird die Aktion gespeichert und nur freigegebene Fragen erscheinen im Quiz für Lerner:innen.

+-------------+-----------------------------------------+
| **Story 7** | **Wissens-Lücken pro Bereich erkennen** |
|             |                                         |
|             | **COULD**                               |
+-------------+-----------------------------------------+

> Als **Stefan** möchte ich sehen, welche Fragen besonders häufig gestellt werden oder oft negatives Feedback bekommen, damit ich gezielt Dokumentation ergänzen oder korrigieren kann.

**Acceptance Criteria**

> **AC1: Given** der Beobachtungszeitraum ist 30 Tage und mindestens 50 Fragen wurden gestellt **When** ich das Dashboard öffne **Then** sehe ich Top-10 Themen-Cluster (gebildet via Embedding-Ähnlichkeit) mit Häufigkeit und aggregierter Feedback-Quote.
>
> **AC2: Given** ich klicke auf einen Cluster mit hoher Negativ-Quote **When** sich die Detailansicht öffnet **Then** sehe ich Beispielfragen sowie die vom System verwendeten Quellen.
>
> **AC3: Given** Cluster werden angezeigt **When** ein Cluster weniger als 5 Fragen enthält **Then** wird er nicht angezeigt (Pseudonymitäts-Schutz).

+-------------+---------------------------------------------+
| **Story 8** | **Authentifizierung und Bereichszuordnung** |
|             |                                             |
|             | **MUST (NEU)**                              |
+-------------+---------------------------------------------+

> Als **Lara** möchte ich mich mit meinen Firmen-Credentials anmelden und automatisch die Bereiche sehen, für die ich freigegeben bin, damit ich nur relevante und für mich freigegebene Inhalte zu sehen bekomme.

**Acceptance Criteria**

> **AC1: Given** ich öffne die Plattform **When** ich nicht authentifiziert bin **Then** werde ich auf den firmeninternen Single-Sign-On weitergeleitet (SSO über Active Directory / Entra ID).
>
> **AC2: Given** ich bin angemeldet **When** ich die Bereichsauswahl öffne **Then** sehe ich nur die Bereiche, für die meine Rolle / mein Team in der Bereichszuordnung freigegeben sind.

+-------------+--------------------------------------------+
| **Story 9** | **Bereiche und Verantwortliche verwalten** |
|             |                                            |
|             | **MUST (NEU)**                             |
+-------------+--------------------------------------------+

> Als **Admin** möchte ich Bereiche anlegen, ihnen Verantwortliche zuordnen und Zugriffsregeln definieren, damit das System ein sauberes organisatorisches Modell hat.

**Acceptance Criteria**

> **AC1: Given** ich bin als Admin angemeldet **When** ich einen neuen Bereich anlege und Verantwortliche zuordne **Then** erhalten diese eine Benachrichtigung mit ihren Rechten und Pflichten (inkl. erwartetem Pflegeaufwand).
>
> **AC2: Given** ein Bereich existiert **When** ich Zugriffsregeln definiere (welche AD-Gruppen / Teams sehen ihn) **Then** werden diese sofort wirksam.

+--------------+-----------------------------------------+
| **Story 10** | **Folgefragen im Konversationskontext** |
|              |                                         |
|              | **SHOULD (NEU)**                        |
+--------------+-----------------------------------------+

> Als **Lara** möchte ich zu einer erhaltenen Antwort Folgefragen stellen können, damit ich Themen iterativ vertiefen kann, ohne den Kontext jedes Mal neu zu erklären.

**Acceptance Criteria**

> **AC1: Given** ich habe eine Antwort erhalten **When** ich eine Folgefrage stelle **Then** berücksichtigt das System die vorangegangenen 1--3 Frage-Antwort-Paare als Kontext und antwortet konsistent.
>
> **AC2: Given** ich starte eine neue Frage zu einem unverwandten Thema **When** ich auf Neues-Gespräch klicke **Then** wird der Kontext zurückgesetzt.

+--------------+------------------------------+
| **Story 11** | **Kaputte Quellen erkennen** |
|              |                              |
|              | **SHOULD (NEU)**             |
+--------------+------------------------------+

> Als **System (im Auftrag der Bereichsverantwortlichen)** möchte ich erkennen, wenn eine im Korpus referenzierte Originalquelle nicht mehr existiert oder geändert wurde, damit Lara keine ins Leere führenden Quellenverweise sieht.

**Acceptance Criteria**

> **AC1: Given** eine Quelle im Korpus stammt aus Confluence/SharePoint **When** die wöchentliche Integritätsprüfung läuft und die Originalquelle nicht mehr erreichbar ist **Then** wird die Quelle im Korpus als broken markiert und nicht mehr für Antworten verwendet.
>
> **AC2: Given** eine Quelle ist als broken markiert **When** Stefan das Dashboard öffnet **Then** sieht er die Liste betroffener Quellen mit Vorschlag Re-Upload / Entfernen.

**Phase 04 · Projekt-Canvas**
=============================

+--------------------------+
| **Projektname**          |
|                          |
| LearnFlow (Arbeitstitel) |
+--------------------------+

+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Was wir bauen -- in einem Satz**                                                                                                                                                                                                                                                                                                            |
|                                                                                                                                                                                                                                                                                                                                               |
| Eine interne Lernplattform, die neuen Entwickler:innen, Requirements-Engineers und Tester:innen das fachliche Domänen- und Systemwissen unserer historisch gewachsenen Fachanwendungen über quellenbelegte KI-Antworten und überprüfte Quizfragen zugänglich macht -- auf Basis eines kuratierten, vom Fachbereich freigegebenen Lern-Korpus. |
+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Zielgruppe (Personas)**                                                                                                                                                                       |
|                                                                                                                                                                                                 |
| Lara, 26, Junior Software Engineer -- muss sich schnell in eine komplexe Fachdomäne einarbeiten. Stefan, 51, Senior BA und Bereichsverantwortlicher -- pflegt den Korpus, gibt Quizfragen frei. |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Problem das wir lösen**                                                                                                                                                                                                                         |
|                                                                                                                                                                                                                                                   |
| Wissen ist über viele Quellen (Confluence, Jira, Code, Workshop-Protokolle) verteilt, oft veraltet und schwer auffindbar. Neue Mitarbeiter:innen verlieren Wochen mit Suchen oder Nachfragen, erfahrene Kolleg:innen werden ständig unterbrochen. |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

+----------------------------------------------------------------+
| **Must-have für MVP (Top 3 User Stories)**                     |
|                                                                |
| Story 1 -- Frage stellen und quellenbelegte Antwort bekommen.\ |
| Story 4 -- Unsichere Antworten klar erkennen.\                 |
| Story 2 -- Inhalte in den Lern-Korpus aufnehmen.               |
+----------------------------------------------------------------+

+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Grösstes Risiko und unser Plan**                                                                                                                                                                                                                                                                       |
|                                                                                                                                                                                                                                                                                                          |
| Content Rot -- die Plattform stirbt an veralteten Inhalten. Plan: (a) verbindliche Pflege-Vereinbarung mit jedem teilnehmenden Bereich vor Aufnahme; (b) monatlicher Stale-Content-Report automatisch; (c) Validierungsdatum sichtbar an jeder Antwort; (d) Pilot bewusst klein -- ein einziger Bereich. |
+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Wo setzen wir AI ein -- konkret**                                                                                                                                                                      |
|                                                                                                                                                                                                          |
| LLM für Antwortgenerierung (RAG); Embedding-Modell für semantisches Retrieval und Themen-Clustering; LLM für Self-Check als Konfidenz-Signal; LLM für Quizfragen-Generierung mit menschlicher Freigabe.\ |
| \                                                                                                                                                                                                        |
| Bewusst KEINE KI bei: Authentifizierung, Pflege-Workflow, Bereichszuordnung -- bleibt deterministisch und auditierbar.                                                                                   |
+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

+------------------------------------------------------------------------------------+
| **Nächste Schritte bis zur Präsentation**                                          |
|                                                                                    |
| 1\. Pilot-Bereich konkret benennen (Bereichsleiter ansprechen).\                   |
| 2. Build-vs-Buy-Kurzanalyse (Atlassian Rovo, Glean, Microsoft Copilot vs. eigen).\ |
| 3. 5--10 echte Beispielfragen sammeln.\                                            |
| 4. LLM-Wahl entscheiden (on-prem vs. Azure OpenAI EU).\                            |
| 5. Mockup der Frage-Antwort-Ansicht erstellen.\                                    |
| 6. Erweiterte Story-Liste im Backlog ablegen.                                      |
+------------------------------------------------------------------------------------+

**Machbarkeits-Analyse: 3 Personen, bis 30. September 2026**
============================================================

+-----------------------------------------------------------------+
| **Verdikt**                                                     |
|                                                                 |
| JA -- machbar, mit klarer Scope-Disziplin und drei Bedingungen. |
+-----------------------------------------------------------------+

**Rahmen**
----------

-   Zeitfenster: 3. Mai -- 30. September 2026 ≈ 21 Wochen / 5 Monate.

-   Team: 3 Personen, CAS-typisch nebenberuflich (geschätzt 8--16 h/Woche/Person -- rund 500--1.000 Personenstunden insgesamt).

-   Anspruch: keine Produktions-MVP, Prototyp und tragfähiges Konzept reicht.

**Was im Rahmen realistisch ist**
---------------------------------

-   Story 1 (Q&A mit Quellen) -- \~120 h

-   Story 4 (Unsichere Antworten) -- \~60 h

-   Story 2 minimal (Upload-UI) -- \~60 h

-   Story 6a (Quiz absolvieren) -- \~80 h

-   Polish, Testing, Doku, Präsentation -- \~120 h

-   Tech-Spike, Architekturentscheidungen, Setup -- \~80 h

*Summe: rund 520 h. Passt komfortabel in 500--1.000 h. Selbst mit Lernkurve im RAG-Bereich (+150 h) bleibt Puffer.*

**Was draussen bleiben muss**
-----------------------------

-   Story 8 (echte SSO-Authentifizierung) -- mock/hardcoded User.

-   Story 9 (Admin-UI für Bereiche) -- ein einziger Pilot-Bereich, hartcodiert.

-   Story 5 (Stale-Content-Erkennung) -- Konzept im Doku, keine Implementierung.

-   Story 6b (Quiz-Freigabe-Workflow) -- Konzept, manuelle Pflege.

-   Stories 7, 10, 11 -- Backlog für nach dem Kurs.

-   Multi-Tenant, Skalierung, Performance-Tuning -- out of scope.

**Drei kritische Bedingungen**
------------------------------

5.  **Tech-Stack in Woche 1 fixiert --** ein Tag Workshop, dann Entscheidung. Bevorzugt Azure OpenAI EU (kein On-Prem-LLM-Abenteuer im Kursrahmen).

6.  **Pilot-Bereich + \~50 echte Dokumente bis Woche 2 --** sonst kein echter Korpus zum Testen, dann wird es eine Demo auf Papier.

7.  **Strenge Scope-Disziplin --** jede neue Story-Idee muss einer auf der Liste oben Platz machen.

**Grobplan**
------------

-   Mai (W1--4): Tech-Spike, Architektur, RAG-Prototyp auf 5 Demo-Dokumenten.

-   Juni--Juli (W5--12): Stories 1, 4, 2, 6a iterativ implementieren.

-   August (W13--17): Testen mit echten Lara-Fragen, Feedback-Schleifen, Quiz fertigstellen.

-   September (W18--21): Polish, Doku, Präsentationsvorbereitung, Reservepuffer.

*Wenn der Scope auf 4 Stories begrenzt wird (ohne Quiz), schaffen es 3 Personen selbst mit einer Person Ausfall. Quiz ist die grösste Einzelschätzung -- wenn die Zeit knapp wird, fliegt sie als Erstes.*

**Anhang · Entscheidungs-Log**
==============================

*Wichtige Entscheidungen aus dem Kickoff -- als Nachschlagewerk.*

  **Thema**                  **Entscheidung**                                                                        **Begründung**
  -------------------------- --------------------------------------------------------------------------------------- -----------------------------------------------------------------------------------------------
  **Anwendungsfall**         Variante 1 (Entwickler:innen lernen Fachdomäne).                                        Eigene Dogfood-Möglichkeit, kleinerer Scope, niedrigeres Risiko.
  **Korpus-Strategie**       Kuratierter Lern-Korpus parallel zu Quellsystemen.                                      Vermeidet Berechtigungsmodell über vier Quellsysteme; klare Pflegeverantwortung.
  **Pflege-Verantwortung**   Organisatorisch ausserhalb des Projekts -- Bereiche bestimmen Verantwortliche selbst.   Kann nicht im Projekt geklärt werden; Mindesterwartung im Canvas dokumentiert.
  **Quellenbelegung**        Pflicht -- Acceptance Criterion in jeder Q&A-Story.                                     Grösste Vertrauens-Mechanik; nicht verhandelbar.
  **Erfolgsmessung**         Nutzungszahlen pro Mitarbeiter:in + Anteil positiver Feedbacks + Mitarbeiter-Umfrage.   Quantitative Signale + qualitative Validierung.
  **Personal-Tracking**      Im MVP raus (Story 8 als Won't).                                                        Datenschutz- und Betriebsrats-Risiko; nach Pilot mit anonymisierten Aggregaten nachschiebbar.
  **LLM-Plattform**          Noch offen -- bevorzugte Richtung Azure OpenAI EU.                                      On-Prem-LLM zu aufwendig im Kursrahmen; Datenschutzfreigabe vorab klären.
  **Pilot-Bereich**          Noch offen.                                                                             Blockt alles Weitere -- höchste Priorität in den nächsten Schritten.

*Begleit-Artefakt: LearnFlow\_Pitch.pptx (5-Minuten-Präsentation).*
