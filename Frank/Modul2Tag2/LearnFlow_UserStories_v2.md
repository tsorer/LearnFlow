# LearnFlow — User Stories v2
## Kombinierte Basis: MoSCoW-Priorisierung + Requirements-Dokument
*Rolle: Requirements Engineer · KI-gestützte Lernplattform für neue Mitarbeitende · Mai 2026*

---

## MUST – Muss umgesetzt werden

### US-01 · Quellenbelegte Frage-Antwort

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich eine Frage in natürlicher Sprache stellen und eine quellenbelegte Antwort erhalten, damit ich Fachprozesse verstehen kann, ohne erfahrene Kolleg:innen zu unterbrechen.*

**Akzeptanzkriterien:**
- ✓ Jede Antwort enthält mindestens einen klickbaren Quellenverweis (Dokumenttitel + Abschnitt + Validierungsdatum).
- ✓ Ein Klick auf eine Quellenangabe öffnet das Originaldokument und hebt den belegenden Abschnitt visuell hervor.
- ✓ Antworten ohne identifizierbare Quelle werden nicht angezeigt.
- ✓ Eingaben unter 3 Zeichen oder über 1.000 Zeichen werden clientseitig abgewiesen mit einem verständlichen Hinweis.
- ✓ Ist der LLM- oder Retrieval-Service nicht erreichbar, erscheint eine klare Fehlermeldung – keine erfundene Antwort.
- ✓ Die Antwortzeit beträgt im 95. Perzentil maximal 10 Sekunden.

---

### US-02 · Unsichere Antworten klar erkennen

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich klar erkennen, wenn das System sich seiner Antwort nicht sicher ist, damit ich keinen halluzinierten Inhalten vertraue und keine falschen Informationen unbemerkt übernehme.*

**Akzeptanzkriterien:**
- ✓ Unterschreitet der Konfidenz-Score einen konfigurierten Schwellenwert, antwortet das System nicht inhaltlich, sondern zeigt: „Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden."
- ✓ Nach Anzeige von „Ich weiß es nicht" gibt das System Lara einen kontextuellen Hinweis, wie sie ihre Frage präzisieren könnte (z. B. „Versuche, einen konkreten Prozess oder ein Dokument zu nennen") – die Reformulierung liegt bei Lara.
- ✓ Liegt der Anteil belegter Aussagen im Self-Check unter 80 %, wird die Antwort als „Eingeschränkt belegt" markiert (Farbe + Icon + Hinweistext).
- ✓ Liegt der Anteil unter 50 %, wird die Antwort vollständig unterdrückt.
- ✓ Der Konfidenz-Score ist in der Antwort-Metainfo einsehbar.
- ✓ Der initiale Schwellenwert wird im Pilotbetrieb empirisch ermittelt; danach ist er über das Admin-Setting konfigurierbar.
- ✓ Das System gibt bei Out-of-Corpus-Testfragen in mindestens 90 % der Fälle ein „Weiss ich nicht" zurück.

---

### US-03 · Feedback zu Antworten geben

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich jede Antwort als hilfreich oder nicht hilfreich markieren und einen Grund angeben, damit unklare oder falsche Antworten erkannt und korrigiert werden können.*

**Akzeptanzkriterien:**
- ✓ Jede Antwort enthält eine Bewertungsmöglichkeit (👍 / 👎).
- ✓ Bei positivem Feedback (👍) wähle ich eine Kategorie: verständlich / vollständig / hilfreich für Code / Quelle passt gut.
- ✓ Bei negativem Feedback (👎) wähle ich eine Kategorie: faktisch falsch / unvollständig / veraltet / unverständlich / Quelle stimmt nicht.
- ✓ Bei beiden Varianten kann ich optional Freitext ergänzen.
- ✓ Nach dem Speichern erhalte ich eine Bestätigung und das Feedback erscheint im Bereichs-Dashboard von Stefan.
- ✓ Feedback wird pseudonymisiert erfasst – keine Rückverfolgung auf einzelne Lernende.

---

### US-04 · Inhalte in den Lernkorpus aufnehmen

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich Dokumente in den Lernkorpus meines Bereichs aufnehmen und freigeben können, damit nur von mir geprüfte Inhalte als Wissensgrundlage für KI-Antworten dienen.*

**Akzeptanzkriterien:**
- ✓ Stefan kann Dokumente in den Formaten PDF, Word (.docx) und Markdown hochladen.
- ✓ Dokumente bis 50 Seiten / 10 MB sind nach maximal 5 Minuten als Quelle verfügbar; grössere Dokumente erhalten eine Fortschrittsanzeige.
- ✓ Hochgeladene Dokumente sind erst nach expliziter Freigabe durch Stefan aktiv.
- ✓ Eine neue Version wird anhand des Dateinamens erkannt: Lädt Stefan eine Datei mit identischem Namen hoch, ersetzt sie automatisch das bestehende Dokument – die neue Version wird sofort aktiv, kein erneuter Freigabeschritt erforderlich.
- ✓ Stefan kann die Freigabe jederzeit widerrufen.
- ✓ Freigegebene Dokumente erhalten einen Zeitstempel, der für Lara sichtbar ist.
- ✓ Nur Dokumente des eigenen Bereichs sind sichtbar und freigabefähig.

---

### US-05 · Authentifizierung und Bereichszuordnung

**Persona:** Lara & Stefan – alle Nutzer

**User Story:**
*Als Plattformnutzerin möchte ich mich sicher anmelden können und automatisch die Bereiche sehen, für die ich freigegeben bin, damit nur autorisierte Mitarbeitende Zugang zur Plattform und zu den relevanten Inhalten haben.*

**Akzeptanzkriterien:**
- ✓ MVP: Authentifizierung per Username/Passwort (lokal verwaltete Accounts).
- ✓ Post-MVP: SSO-Anbindung via Unternehmens-IdP (z. B. Azure AD / SAML 2.0) geplant.
- ✓ Nicht authentifizierte Nutzer werden auf die Login-Seite weitergeleitet.
- ✓ Nach dem Login sieht jede Person nur die Bereiche, für die sie freigeschaltet ist.
- ✓ Rollen (Lernende / Bereichsverantwortliche) werden manuell beim Account-Setup zugewiesen (MVP); post-MVP aus dem IdP übernommen.

---

## SHOULD – Sollte umgesetzt werden

### US-06 · Veraltete Inhalte erkennen und re-validieren

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich eine Übersicht über veraltete Inhalte erhalten und diese aktiv re-validieren können, damit der Lernkorpus meines Bereichs stets aktuell bleibt.*

**Akzeptanzkriterien:**
- ✓ Das Dashboard zeigt alle Dokumente, die seit mehr als 90 Tagen nicht validiert wurden, sortiert nach Alter und letztem Validierungsdatum.
- ✓ Klickt Stefan auf einen Eintrag, kann er den Inhalt als „aktuell", „ersetzt durch …" oder „entfernen" markieren.
- ✓ Stefan erhält einmal pro Monat automatisch einen E-Mail-Report mit der Liste veralteter Dokumente und einem Direktlink zur Freigabeoberfläche.
- ✓ Stefan kann den Schwellenwert (Tage bis „stale") selbst konfigurieren.

> **Post-MVP:** Inhaltlicher Diff zwischen alter und neuer Dokumentversion – Stefan sieht beim Upload, welche Abschnitte sich geändert haben, und kann gezielt nur die betroffenen Stellen re-validieren.

---

### US-07 · KI-generierte Quiz-Fragen prüfen und freigeben

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich vom LLM vorgeschlagene Multiple-Choice-Fragen prüfen und gezielt freigeben oder ablehnen, damit nur validierte Quizfragen in der Lernkontrolle verwendet werden.*

**Akzeptanzkriterien:**
- ✓ Stefan löst die Quiz-Generierung manuell per Klick aus; das System erstellt daraufhin Vorschläge aus den freigegebenen Dokumenten des Bereichs.
- ✓ Stefan sieht alle offenen Fragen in einem Review-Dashboard, inklusive der Quellen-Passage, aus der sie generiert wurden.
- ✓ Er kann Fragen einzeln freigeben, ablehnen oder editieren.
- ✓ Abgelehnte Fragen sind für Lernende nicht sichtbar.
- ✓ Freigegebene Fragen erhalten einen Zeitstempel.

---

### US-08 · Quiz absolvieren

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich zu einem Bereich ein kurzes Quiz absolvieren, damit ich überprüfen kann, ob ich das Gelesene wirklich verstanden habe.*

**Akzeptanzkriterien:**
- ✓ Lara kann pro Bereich ein Quiz mit 5 Multiple-Choice-Fragen aus dem Pool freigegebener Quizfragen starten.
- ✓ Sind noch keine Quizfragen für einen Bereich freigegeben, ist der Button sichtbar, zeigt aber den Hinweis: „Es sind noch keine Quizfragen für diesen Bereich freigegeben."
- ✓ Nach Abschluss sieht Lara pro Frage: richtig/falsch, die korrekte Antwort mit Erklärung und einen direkten Link zur belegenden Quelle.
- ✓ Quiz-Ergebnisse werden nicht personenbezogen gespeichert oder ausgewertet.

> **Voraussetzung:** US-07 muss implementiert und mindestens eine Quizfrage freigegeben sein.

---

## COULD – Kann umgesetzt werden

### US-09 · Folgefragen im Gesprächskontext stellen

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich nach einer Antwort Folgefragen im gleichen Kontext stellen können, damit ich ein Thema schrittweise vertiefen kann, ohne den Kontext jedes Mal neu zu erklären.*

**Akzeptanzkriterien:**
- ✓ Vorherige Fragen und Antworten der Sitzung (max. 3 Frage-Antwort-Paare) fließen als Kontext in Folgefragen ein.
- ✓ Die Gesprächshistorie der Session ist für Lara sichtbar (Scroll-Verlauf).
- ✓ Lara kann jederzeit eine neue Konversation starten (Context reset).
- ✓ Quellenverweise aus vorherigen Antworten bleiben in der Sitzung verlinkt.
- ✓ Die Gesprächshistorie ist nur für die aktive Browser-Session gültig; beim Schließen des Browsers wird der Kontext verworfen.

---

### US-10 · Wissens-Lücken im Bereich erkennen

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich sehen, welche Fragen besonders häufig gestellt werden oder oft negatives Feedback erhalten, damit ich gezielt Dokumentation ergänzen oder korrigieren kann.*

**Akzeptanzkriterien:**
- ✓ Stefan kann den Mindest-Schwellenwert für die Cluster-Anzeige selbst konfigurieren (Standard: 30 Tage Beobachtungszeitraum, mindestens 20 gestellte Fragen).
- ✓ Das Dashboard zeigt die Top-10-Themen-Cluster (gebildet via Embedding-Ähnlichkeit) mit Häufigkeit und aggregierter Feedback-Quote – sobald der konfigurierte Schwellenwert erreicht ist.
- ✓ Cluster mit weniger als 5 Fragen werden nicht angezeigt (Pseudonymitäts-Schutz).
- ✓ Ein Klick auf einen Cluster zeigt Beispielfragen sowie die vom System verwendeten Quellen.
- ✓ Stefan kann direkt aus dem Cluster-Detail einen Dokument-Upload oder eine Re-Validierung anstoßen.

---

## MoSCoW-Legende

| MUST | SHOULD | COULD |
|------|--------|-------|
| Muss umgesetzt werden | Sollte umgesetzt werden | Kann umgesetzt werden |

---

*Quellen: LearnFlow_UserStories_MoSCoW.md (refinement session) + LearnFlow_Requirements_nick.md (v1.1)*
