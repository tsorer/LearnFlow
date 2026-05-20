# LearnFlow — MoSCoW-Analyse & Widersprüche
*Modul 2 Tag 2 · Selbststudium · Frank Moritz · Mai 2026*

---

## Phase 01 · MoSCoW-Priorisierung

*Quelle: `LearnFlow_UserStories_v2.md` (überarbeitete Version)*

| # | User Story | MoSCoW | Begründung |
|---|-----------|--------|-----------|
| 1 | **US-01** · Als Junior-Entwicklerin möchte ich eine Frage in natürlicher Sprache stellen und eine quellenbelegte Antwort erhalten | **MUST** | Kernfunktion der Plattform — ohne Q&A mit Quellenbeleg existiert das Produkt nicht |
| 2 | **US-02** · Als Junior-Entwicklerin möchte ich klar erkennen, wenn das System sich seiner Antwort nicht sicher ist | **MUST** | Vertrauensbasis — nicht erkannte Halluzinationen zerstören sofort das Vertrauen der Zielgruppe |
| 3 | **US-03** · Als Junior-Entwicklerin möchte ich jede Antwort als hilfreich oder nicht hilfreich markieren und einen Grund angeben | **MUST** | Qualitätssicherungsschleife — ohne Feedback hat Stefan keinen Weg, Fehler zu erkennen und zu korrigieren |
| 4 | **US-04** · Als Bereichsverantwortlicher möchte ich Dokumente in den Lernkorpus meines Bereichs aufnehmen und freigeben | **MUST** | Kein Korpus = keine Antworten — die Content-Management-Grundlage für alles andere |
| 5 | **US-05** · Als Plattformnutzerin möchte ich mich sicher anmelden und automatisch nur freigegebene Bereiche sehen | **MUST** | Zugangskontrolle und Datentrennung zwischen Bereichen sind nicht verhandelbar |
| 6 | **US-06** · Als Bereichsverantwortlicher möchte ich eine Übersicht über veraltete Inhalte erhalten und diese re-validieren können | **SHOULD** | Wichtig für langfristige Qualität, aber kurzfristig kein Blocker — Plattform funktioniert auch ohne, verliert aber über Zeit an Vertrauen |
| 7 | **US-07** · Als Bereichsverantwortlicher möchte ich KI-generierte Quiz-Fragen prüfen und gezielt freigeben oder ablehnen | **SHOULD** | Direkte Voraussetzung für US-08 — beide SHOULD, da das Quiz nicht zum Q&A-Kern gehört |
| 8 | **US-08** · Als Junior-Entwicklerin möchte ich zu einem Bereich ein kurzes Quiz absolvieren | **SHOULD** | Wertvoller Lerncheck; setzt US-07 voraus — nützlich, aber kein Blocker für den Haupt-Use-Case |
| 9 | **US-09** · Als Junior-Entwicklerin möchte ich nach einer Antwort Folgefragen im gleichen Kontext stellen | **COULD** | Nice-to-have — Lara kann auch ohne gespeicherten Kontext erneut fragen; reduziert Komfort, nicht Kernfunktion |
| 10 | **US-10** · Als Bereichsverantwortlicher möchte ich sehen, welche Fragen besonders häufig gestellt werden oder oft negatives Feedback erhalten | **COULD** | Wertvolle Analyse-Funktion, braucht aber erst signifikante Nutzungsdaten als Basis — zu früh im MVP sinnlos |

> **Hinweis:** Mehr als 4–5 Must-haves sind ein Warnsignal. Hier sind es 5 MUST-Stories —
> US-05 (Authentifizierung) wurde bewusst als MUST bewertet, da ohne Zugangskontrolle keine
> bereichsbezogene Datentrennung möglich ist. US-01–04 sind der absolute Kern des RAG-Ansatzes.

---

## Phase 01 · Widersprüche

*Gefundene interne Widersprüche innerhalb der 10 User Stories aus `LearnFlow_UserStories_v2.md`*

---

### Widerspruch 1 · US-04: Freigabepflicht vs. automatische Aktivierung bei Versionsupdate

**Betrifft:** US-04 · Inhalte in den Lernkorpus aufnehmen

Zwei Akzeptanzkriterien derselben Story widersprechen sich direkt:

> AC: *„Hochgeladene Dokumente sind erst nach expliziter Freigabe durch Stefan aktiv."*

> AC: *„Lädt Stefan eine Datei mit identischem Namen hoch, ersetzt sie automatisch das bestehende Dokument – die neue Version wird **sofort aktiv**, kein erneuter Freigabeschritt erforderlich."*

**Problem:** Beim ersten Upload eines Dokuments ist die Freigabe Pflicht. Bei einem Versionsupdate (gleicher Dateiname) wird diese Freigabe übersprungen. Ein und dasselbe Dokument hat je nach Upload-Weg zwei verschiedene Freigaberegeln — das öffnet einen Bypass des Qualitäts-Gates. Stefan könnte versehentlich ungeprüfte Inhalte aktivieren, indem er denselben Dateinamen verwendet.

**Lösungsvorschlag:** Entweder auch Versionsupdates durch eine explizite Freigabe bestätigen lassen — oder die Absicht klarstellen: *„Stefan vertraut dem Update implizit, weil er es selbst ausgelöst hat."* In letzterem Fall sollte das AC entsprechend formuliert sein.

---

### Widerspruch 2 · US-01 vs. US-02: Was gilt als „Antwort ohne Quelle"?

**Betrifft:** US-01 · Quellenbelegte Frage-Antwort ↔ US-02 · Unsichere Antworten klar erkennen

> US-01 AC: *„Antworten ohne identifizierbare Quelle werden nicht angezeigt."*

> US-02 AC: *„Liegt der Anteil belegter Aussagen im Self-Check unter 80 %, wird die Antwort als 'Eingeschränkt belegt' markiert"* — also: die Antwort wird trotzdem gezeigt.

**Problem:** US-01 verbietet Antworten ohne Quelle. US-02 erlaubt Antworten, bei denen bis zu 20 % der Aussagen unbelegt sind — mit Marker, aber sichtbar. Was gilt als „ohne identifizierbare Quelle": null Quellen, oder ein Anteil unter einem bestimmten Schwellenwert? Für die Implementierung ist unklar, welche Regel greift, wenn eine Antwort z. B. zu 60 % belegt ist.

**Lösungsvorschlag:** US-01 AC präzisieren: *„Antworten, die keiner einzigen Quelle zugeordnet werden können"* → dann deckt US-02 die Teilbelegung ab. Oder: Die Schwellenwerte aus US-02 (80 % / 50 %) explizit als Sonderfall in US-01 referenzieren.

---

### Widerspruch 3 · US-02: Zwei Unterdrückungsmechanismen — fehlende Nutzermeldung im zweiten Fall

**Betrifft:** US-02 · Unsichere Antworten klar erkennen (intern)

US-02 beschreibt zwei separate Mechanismen, die beide zur vollständigen Antwortunterdrückung führen:

| Zeitpunkt | Auslöser | Nutzermeldung |
|-----------|---------|--------------|
| **Vor** der Generierung | Konfidenz-Score < konfigurierter Schwellenwert | *„Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden."* |
| **Nach** der Generierung | Self-Check-Anteil < 50 % | Antwort unterdrückt — **keine Meldung definiert** |

**Problem:** Wenn der Konfidenz-Score ausreichend ist (Antwort wird generiert), aber der nachfolgende Self-Check unter 50 % fällt, wird die Antwort still unterdrückt. Das AC legt keine Nutzermeldung für diesen Fall fest. Aus Lara's Perspektive: Sie stellt eine Frage und sieht — nichts, ohne zu wissen warum. Das erzeugt Verwirrung und untergräbt das Vertrauen.

**Lösungsvorschlag:** Für den Post-Generierungs-Fall eine explizite Nutzermeldung definieren, z. B. *„Die generierte Antwort konnte nicht ausreichend belegt werden und wird nicht angezeigt."* Und klarstellen, ob beide Mechanismen die identische Meldung zeigen sollen oder bewusst unterschiedlich kommunizieren.

---

---

## Phase 02 · Gaps finden — Die 5 wichtigsten fehlenden Szenarien

*Analyse der 10 User Stories auf nicht abgedeckte Bereiche*

---

### Fehlendes Szenario 1 · Benutzer- und Bereichsverwaltung (Admin-Flow)

**Kategorie:** Admin-Flow / fehlende Story

US-05 setzt voraus, dass Rollen und Bereichszuordnungen existieren — erklärt aber nicht, wer sie anlegt, ändert oder löscht. Die Fragen bleiben komplett offen:

- Wer legt einen neuen Bereich an?
- Wer erstellt Lara's Account und weist sie dem Sozialdienste-Bereich zu?
- Wer setzt Stefan als Bereichsverantwortlichen?
- Was passiert, wenn Lara das Unternehmen verlässt oder Stefan ersetzt wird?

Ohne Admin-Flow ist das System nicht betreibbar. Das ist eine fehlende MUST-Story, nicht ein Nice-to-have. *(Im Kickoff-Dokument existierte Story 9 „Bereiche und Verantwortliche verwalten" als MUST NEU — sie fehlt in v2 komplett.)*

---

### Fehlendes Szenario 2 · Kaputte und nicht mehr erreichbare Quellen

**Kategorie:** Error Case / Edge Case

US-01 verlangt, dass ein Klick auf eine Quellenangabe das Originaldokument öffnet und den belegenden Abschnitt hervorhebt. Nicht abgedeckt ist:

- Die verlinkte Confluence-Seite wurde gelöscht oder umbenannt.
- Das SharePoint-Dokument wurde verschoben oder hat neue Zugriffsrechte.
- Stefan hat ein Dokument aus dem Korpus entfernt, aber Antworten referenzieren es noch.

Für Lara sieht das so aus: Sie klickt auf eine Quelle und landet auf einer 404-Seite — genau das Szenario, das das Vertrauen in die Plattform zerstört. Eine Prüfung auf erreichbare Quellen (wöchentlich o. ä.) und eine saubere Fehlermeldung fehlen völlig.

---

### Fehlendes Szenario 3 · DSGVO / Datenlöschung und Datenretention

**Kategorie:** Datenschutz / DSGVO

Die Stories berühren Privacy punktuell (US-03: Pseudonymisierung; US-08: keine Speicherung von Quiz-Ergebnissen; US-10: Cluster-Mindestgrösse 5), aber keiner der folgenden Punkte ist abgedeckt:

- **Retention:** Wie lange werden gestellte Fragen für US-10 (Cluster-Analyse) gespeichert? Nach 30 Tagen Beobachtungszeitraum löschen?
- **Löschrecht:** Was passiert mit Laras pseudonymisierten Fragen, wenn sie das Unternehmen verlässt?
- **Audit-Trail:** Wer hat wann welches Dokument freigeschaltet oder widerrufen? (Relevant für Compliance und Betriebsrat.)
- **Betriebsrat-Konformität:** US-03-Feedback könnte bei ausreichend kleinen Teams de-anonymisiert werden — die Pseudonymisierung allein reicht möglicherweise nicht aus.

---

### Fehlendes Szenario 4 · Cold Start / leerer Korpus

**Kategorie:** Edge Case / Onboarding

Kein einziges AC behandelt den Zustand, bevor der erste Upload stattgefunden hat:

- Was sieht Lara, wenn ihr Bereich noch keine freigegebenen Dokumente enthält?
- Was passiert, wenn Stefan einen Bereich hat, aber noch kein einziges Dokument hochgeladen hat — kann Lara trotzdem fragen?
- Was zeigt das System bei einer Frage gegen einen leeren Korpus? (US-02 setzt voraus, dass ein Retrieval stattfindet — aber was, wenn nichts da ist?)

US-08 enthält bereits einen Hinweis für den leeren Quiz-Pool (*„Es sind noch keine Quizfragen freigegeben"*) — das gleiche Muster fehlt für den Haupt-Use-Case Q&A.

---

### Fehlendes Szenario 5 · Gleichzeitige Bearbeitung und Konflikte

**Kategorie:** Edge Case / Concurrency

Die Stories gehen implizit von einem einzigen Bereichsverantwortlichen aus. Nicht abgedeckt:

- Was passiert, wenn zwei Admins gleichzeitig dasselbe Dokument hochladen oder freigeben?
- Was passiert, wenn Stefan ein Dokument freigibt, während Lara gerade eine Antwort darauf liest, die auf der alten Version basiert?
- Was passiert, wenn Stefan eine Freigabe widerruft (US-04 AC: *„Stefan kann die Freigabe jederzeit widerrufen"*), während Lara gerade die darauf basierende Antwort liest und auf die Quelle klickt?

Das letzte Szenario ist besonders heikel: Lara klickt auf einen Quellenlink, der in dem Moment aus dem Korpus entfernt wird — US-01 und US-04 zusammen ergeben hier einen Race Condition Edge Case ohne definiertes Verhalten.

---

### Phase 02 · Technik 2 — Gefundene Widersprüche

*Tiefergehende Widerspruchsanalyse nach der Gap-Analyse — ergänzt die drei Widersprüche aus Phase 01*

---

**Widerspruch 4 — US-04: Freigabe-Zeitstempel für Lara wird bei Auto-Replace nicht aktualisiert**

*Betrifft:* US-04 · Inhalte in den Lernkorpus aufnehmen

- AC: *„Freigegebene Dokumente erhalten einen Zeitstempel, der für Lara sichtbar ist."*
- AC: *„Die neue Version wird sofort aktiv, kein erneuter Freigabeschritt erforderlich."*

Beim automatischen Versionsupdate (gleicher Dateiname) findet keine neue Freigabe statt — also entsteht auch kein neuer Freigabe-Zeitstempel. Lara sieht das Datum der ursprünglichen Freigabe, obwohl der Inhalt bereits geändert wurde. Das ist das Gegenteil des intendierten Vertrauens-Signals: Der Zeitstempel soll zeigen, wie aktuell eine Quelle ist — nach einem stillen Update zeigt er das Falsche.

---

**Widerspruch 5 — US-06: Konfigurierbarer Staleness-Schwellenwert vs. hartkodierter monatlicher Berichts-Rhythmus**

*Betrifft:* US-06 · Veraltete Inhalte erkennen und re-validieren

- AC: *„Stefan kann den Schwellenwert (Tage bis 'stale') selbst konfigurieren."*
- AC: *„Stefan erhält einmal pro Monat automatisch einen E-Mail-Report."*

Die Konfigurierbarkeit des Schwellenwerts und der fixe monatliche Rhythmus passen nicht zusammen. Beispiele:
- Stefan setzt den Schwellenwert auf **7 Tage** → Dokumente werden extrem schnell stale, aber der Bericht kommt trotzdem nur monatlich — bis dahin hat er längst den Überblick verloren.
- Stefan setzt den Schwellenwert auf **365 Tage** → Der monatliche Bericht ist fast immer leer und damit wertlos.

Der Rhythmus des Reports sollte entweder ebenfalls konfigurierbar sein — oder der Schwellenwert sollte sinnvoll an den Report-Rhythmus gebunden werden.

---

**Widerspruch 6 — US-10: Beispielfragen in Cluster-Detail vs. US-03: Pseudonymisierungsversprechen**

*Betrifft:* US-10 · Wissens-Lücken erkennen ↔ US-03 · Feedback zu Antworten geben

- US-10 AC: *„Ein Klick auf einen Cluster zeigt Beispielfragen sowie die vom System verwendeten Quellen."*
- US-03 AC: *„Feedback wird pseudonymisiert erfasst – keine Rückverfolgung auf einzelne Lernende."*

US-03 pseudonymisiert Feedback. US-10 zeigt konkrete Beispielfragen aus einem Cluster. In kleinen Teams (z. B. 3–4 Entwickler:innen in einem Pilotbereich) können sehr spezifische oder ungewöhnliche Fragen leicht einer Person zugeordnet werden — auch ohne Namen, allein durch Kontext, Schreibstil oder Thema. Das Pseudonymisierungsversprechen aus US-03 ist faktisch nicht einlösbar, wenn die Rohdaten (Beispielfragen) für Stefan sichtbar sind.

Der Schutz in US-10 (Cluster mit < 5 Fragen nicht anzeigen) schützt vor kleinen Clustern — aber nicht vor de-anonymisierenden Einzelfragen innerhalb grösserer Cluster.

---

### Phase 02 · Technik 3 — Was der skeptische CTO ablehnen würde

---

**Einwand 1 — Der Self-Check in US-02 ist ein LLM, das sich selbst bewertet**

US-02 setzt voraus, dass das Modell nach der Generierung selbst prüft, ob seine Antwort vollständig aus den Quellen belegbar ist. Das ist systematisch schwach: LLMs sind nachweislich schlecht darin, eigene Halluzinationen zu erkennen — ein "80 % sicher" vom gleichen Modell ist kein unabhängiges Qualitätssignal. Ein CTO würde fragen: Wer hat das gemessen? Auf welchem Test-Set? Mit welcher Baseline? Ohne empirische Kalibrierung ist der Self-Check-Mechanismus ein Vertrauenstheatre, keine echte Sicherheitsnetz.

**Einwand 2 — Die 10-Sekunden-SLA in US-01 ist unbelegt und riskant**

Eine RAG-Pipeline unter Last umfasst: Query-Embedding → Vektorsuche → (optionales Reranking) → LLM-Generierung → Self-Check. Über eine externe API (Azure OpenAI) mit variablen Latenzzeiten im 95. Perzentil unter 10 Sekunden zu bleiben ist ambitioniert. Dieser Wert wurde offensichtlich nicht durch Messungen auf der geplanten Infrastruktur abgeleitet. Wird er verfehlt, steht die gesamte Story 01 unter Frage — und damit der MVP.

**Einwand 3 — Kein Rollback bei versehentlichem Dokument-Überschreiben (US-04)**

Die Versionsverwaltung in US-04 besteht aus einer einzigen Regel: gleicher Dateiname = neue Version, sofort aktiv. Es gibt keine Versionshistorie, kein Rollback, keine Warnung bei inhaltlich stark abweichenden Dokumenten. Stefan lädt aus Versehen die falsche Datei hoch — die alte Version ist weg, alle Antworten basieren sofort auf dem neuen Inhalt. Das ist für ein produktives System inakzeptabel.

**Einwand 4 — Corpus-Isolation zwischen Bereichen ist nicht spezifiziert**

Kein AC in den 10 Stories beschreibt, wie Bereiche auf Datenbankebene voneinander isoliert sind. Für den Pilot mit einem Bereich ist das unkritisch. Soll das System auf 5–10 Bereiche wachsen, ist die Architekturentscheidung (eigene Vektordatenbank-Indizes pro Bereich? Namespace-basierte Filterung?) fundamental — und sie muss vor dem ersten Commit getroffen werden, nicht nachher.

---

### Phase 02 · Technik 4 — Worst-Case-Szenarien

---

**Worst Case 1 — Eine einzige plausible Falschantwort zerstört das Vertrauen dauerhaft**

Das wahrscheinlichste Scheitern: Das System generiert eine Antwort, die korrekt klingt, eine echte Quelle verlinkt, aber den Sachverhalt falsch darstellt (z. B. eine Sozialleistungsberechnung mit falschen Grenzwerten). Lara implementiert es, der Fehler fällt erst im Code-Review oder im Produktionsbetrieb auf. Im Team geht rum: "LearnFlow hat uns eine falsche Berechnung eingebaut." Ab diesem Moment wird das Tool nicht mehr genutzt — egal wie gut alle anderen Antworten sind. Es gibt nur einen ersten Eindruck.

**Worst Case 2 — Stefan kuratiert nicht und das System degradiert still**

Der Betrieb hängt vollständig an Stefans Bereitschaft, Dokumente zu pflegen und freizugeben. Wenn er die Pflege vernachlässigt (zu viel Tagesgeschäft, wechselt Rolle, verlässt das Unternehmen), veraltet der Corpus — ohne dass irgendjemand es sofort merkt. US-06 schickt einen monatlichen Report, aber wenn niemand reagiert, ist der einzige Effekt: Das System antwortet weiter, aber auf veralteter Grundlage. Content Rot ist lautlos und fatal.

**Worst Case 3 — Datenschutzverletzung durch ungeprüfte Corpus-Inhalte**

Es gibt keine Story, die prüft, ob ein hochgeladenes Dokument personenbezogene oder vertrauliche Daten enthält (HR-Unterlagen, Kundendaten, Gehaltsinfos). Stefan lädt versehentlich ein falsches Dokument hoch — das System indexiert es, generiert Antworten daraus und zeigt Lara Inhalte, die sie nie hätte sehen dürfen. Das ist eine DSGVO-Verletzung. Kein AC in US-04 enthält eine Prüfung auf sensitive Inhalte oder eine Zugriffsklassifizierung.

**Worst Case 4 — Build-vs.-Buy-Fenster schliesst sich während der Entwicklung**

Atlassian Rovo, Microsoft 365 Copilot oder ein vergleichbares Produkt erreicht während der 5-monatigen Entwicklungszeit eine Feature-Parität mit dem geplanten MVP — zu einem Bruchteil des Aufwands und mit Enterprise-Support. Das Alleinstellungsmerkmal von LearnFlow (kuratierbarer Corpus mit Bereichs-Freigabe und validiertem Quiz) muss bis zum Ende des Projekts noch als echter Differenzierungsvorteil erkennbar sein. Andernfalls ist die Antwort auf die Build-vs.-Buy-Frage zum Zeitpunkt der Präsentation bereits "Buy".

---

*Erstellt anhand von `LearnFlow_UserStories_v2.md` · Modul 2 Tag 2 · Mai 2026*
