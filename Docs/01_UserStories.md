# LearnFlow — User Stories v3
## MoSCoW-Priorisierung · MVP 3 Monate · Team 4 Personen
*Rolle: Requirements Engineer · KI-gestützte Lernplattform für neue Mitarbeitende · Mai 2026*

**Änderungen gegenüber v2:**
- US-04: Dokumente werden sofort mit dem Upload aktiv – kein separater Freigabeschritt.
- US-11: Neue Story «Minimale Adminverwaltung» (SHOULD) – schliesst die Lücken User-Management und Systemkonfiguration aus US-02, US-05 und US-06.

**Änderungen (Entscheide 2026-06-10):**
- **Rollenmodell: drei Rollen** — Lernende (Lara) und Bereichsverantwortlicher (Stefan) als Anwender plus Administrator (arbeitet im Hintergrund: Systemkonfiguration). Hebt die frühere Zusammenfassung zu „User/Admin" auf.
- **Budget:** 360 h stehen für die **Umsetzung** zur Verfügung (von 480 h gesamt; die übrigen ~120 h für Planung/Analyse/Architektur).

**Änderungen gegenüber v3 (Entscheide 2026-05-20):**
- MVP-Constraint: genau **ein Bereich** (Pilot-Bereich, hartcodiert).
- User-Management: kein Admin-UI — Accounts werden per **DB-Script** angelegt (Felder: username, passwort, Rolle: Lernende / Bereichsverantwortlicher / Admin). US-11 entfällt als Abhängigkeit für US-05.
- US-11: auf reine Systemkonfiguration reduziert (Konfidenz- und Stale-Schwellenwert); kein User-Management mehr im Scope.
- US-06: **Post-MVP** — Stale-Content-Erkennung inkl. E-Mail-Report wird nicht im MVP umgesetzt. SMTP-Provider-Entscheid entfällt damit als Blocker. US-11-Abhängigkeit (Stale-Schwellenwert) bleibt erhalten, da der Wert künftig benötigt wird.

---

## MVP-Constraints

| Constraint | Wert |
|---|---|
| Anzahl Bereiche | **1** (Pilot-Bereich, hartcodiert) |
| User-Management | **DB-Script** — kein Admin-UI; Felder: username, passwort, Rolle (Lernende / Bereichsverantwortlicher / Admin) |
| Systemkonfiguration | **DB-Script** — Konfidenz- und Stale-Schwellenwert direkt in DB änderbar; alternativ via Admin-Seite (US-11) |
| Authentifizierung | Username / Passwort (lokal); post-MVP SSO via IdP |
| Rollen | **Lernende** (Anwender: fragen, Feedback, Quiz) / **Bereichsverantwortlicher** (Anwender + Dokumente & Quiz verwalten) / **Admin** (Systemkonfiguration im Hintergrund) |

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
- ✓ Nach Anzeige von „Ich weiss es nicht" gibt das System Lara einen kontextuellen Hinweis, wie sie ihre Frage präzisieren könnte (z. B. „Versuche, einen konkreten Prozess oder ein Dokument zu nennen") – die Reformulierung liegt bei Lara.
- ✓ Liegt der Anteil belegter Aussagen im Self-Check unter 80 %, wird die Antwort als „Eingeschränkt belegt" markiert (Farbe + Icon + Hinweistext).
- ✓ Liegt der Anteil unter 50 %, wird die Antwort vollständig unterdrückt.
- ✓ Der Konfidenz-Score ist in der Antwort-Metainfo einsehbar.
- ✓ Der initiale Schwellenwert wird im Pilotbetrieb empirisch ermittelt; danach ist er per DB-Script oder über die Admin-Seite (US-11) änderbar – kein Code-Deployment erforderlich.
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
*Als Bereichsverantwortlicher möchte ich Dokumente in den Lernkorpus meines Bereichs aufnehmen können, damit nur von mir verwaltete Inhalte als Wissensgrundlage für KI-Antworten dienen.*

**Akzeptanzkriterien:**
- ✓ Stefan kann Dokumente in den Formaten PDF, Word (.docx) und Markdown hochladen.
- ✓ Maximale Dateigrösse **10 MB** (hartes Limit, serverseitig durchgesetzt); grössere Dateien werden mit einem verständlichen Hinweis abgewiesen.
- ✓ Dokumente bis 50 Seiten / 10 MB sind nach maximal 5 Minuten als Quelle verfügbar; während der Verarbeitung wird eine Fortschrittsanzeige gezeigt.
- ✓ Eine neue Version (gleicher Dateiname) ersetzt automatisch das bestehende Dokument.
- ✓ Stefan kann ein Dokument jederzeit löschen.
- ✓ Hochgeladene Dokumente erhalten einen Zeitstempel, der für Lara sichtbar ist.
- ✓ Nur Dokumente des eigenen Bereichs sind sichtbar und verwaltbar.

---

### US-05 · Authentifizierung und Bereichszuordnung

**Persona:** Lara & Stefan – alle Nutzer

**User Story:**
*Als Plattformnutzerin möchte ich mich sicher anmelden können und automatisch den Bereich sehen, dem ich zugeordnet bin, damit nur autorisierte Mitarbeitende Zugang zur Plattform und zu den relevanten Inhalten haben.*

**Akzeptanzkriterien:**
- ✓ MVP: Authentifizierung per Username/Passwort; Accounts werden per DB-Script angelegt (Felder: username, passwort, Rolle: Lernende / Bereichsverantwortlicher / Admin) – keine Self-Service-Registrierung.
- ✓ Post-MVP: SSO-Anbindung via Unternehmens-IdP (z. B. Azure AD / SAML 2.0) geplant.
- ✓ Nicht authentifizierte Nutzer werden auf die Login-Seite weitergeleitet.
- ✓ MVP: Nach dem Login sieht jede Person den Pilot-Bereich (genau ein Bereich, hartcodiert).
- ✓ Rollen (Lernende / Bereichsverantwortlicher / Admin) werden beim Account-Anlegen im DB-Script gesetzt; post-MVP aus dem IdP übernommen.

---

## SHOULD – Sollte umgesetzt werden

### US-06 · Veraltete Inhalte erkennen und re-validieren *(Post-MVP)*

> **Entscheid (2026-06-04):** US-06 wird nicht im MVP umgesetzt. E-Mail-Report erfordert SMTP-Provider, der im MVP-Zeitrahmen nicht eingeplant ist. Die Dashboard-Ansicht für Stale-Dokumente und der E-Mail-Report kommen nach dem Pilot.

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich eine Übersicht über veraltete Inhalte erhalten und diese aktiv re-validieren können, damit der Lernkorpus meines Bereichs stets aktuell bleibt.*

**Akzeptanzkriterien:**
- ✓ Das Dashboard zeigt alle Dokumente, die seit mehr als 90 Tagen nicht validiert wurden, sortiert nach Alter und letztem Validierungsdatum.
- ✓ Klickt Stefan auf einen Eintrag, kann er den Inhalt als „aktuell", „ersetzt durch …" oder „entfernen" markieren.
- ✓ Stefan erhält einmal pro Monat automatisch einen E-Mail-Report mit der Liste veralteter Dokumente und einem Direktlink zum Dokument-Dashboard.
- ✓ Der Stale-Schwellenwert (Standard: 90 Tage) ist per DB-Script oder über die Admin-Seite (US-11) änderbar – kein Code-Deployment erforderlich.

> **Post-MVP:** Inhaltlicher Diff zwischen alter und neuer Dokumentversion – Stefan sieht beim Upload, welche Abschnitte sich geändert haben, und kann gezielt nur die betroffenen Stellen re-validieren.

---

### US-07 · KI-generierte Quiz-Fragen prüfen und freigeben

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich vom LLM vorgeschlagene Multiple-Choice-Fragen prüfen und gezielt freigeben oder ablehnen, damit nur validierte Quizfragen in der Lernkontrolle verwendet werden.*

**Akzeptanzkriterien:**
- ✓ Stefan löst die Quiz-Generierung manuell per Klick aus; das System erstellt daraufhin Vorschläge aus den Dokumenten des Bereichs.
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

### US-11 · Systemkonfiguration über Admin-Seite

**Persona:** Admin – technisch verantwortliche Person im Team

**User Story:**
*Als Admin möchte ich Systemparameter über eine geschützte Seite anpassen können, damit ich Konfidenz- und Stale-Schwellenwerte ohne Code-Deployment ändern kann.*

**Akzeptanzkriterien:**
- ✓ Admin kann den Konfidenz-Schwellenwert (US-02) und den Stale-Schwellenwert in Tagen (US-06) über eine passwortgeschützte Admin-Seite anpassen; Änderungen wirken sofort ohne Neustart.
- ✓ Beide Werte sind alternativ auch per DB-Script änderbar (Fallback ohne UI).
- ✓ Konfigurationsänderungen werden mit Zeitstempel und ausführender Person protokolliert.
- ✓ Die Admin-Seite ist ausschliesslich für Accounts mit Admin-Rolle erreichbar; direkter URL-Aufruf ohne Admin-Rechte wird abgewiesen.

> **Nicht im Scope:** User-Management (erfolgt per DB-Script, siehe MVP-Constraints).
> **Abhängigkeiten:** Wird von US-02 (Konfidenz-Konfiguration) und US-06 (Stale-Konfiguration) referenziert.

---

## COULD – Kann umgesetzt werden

### US-09 · Folgefragen im Gesprächskontext stellen

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich nach einer Antwort Folgefragen im gleichen Kontext stellen können, damit ich ein Thema schrittweise vertiefen kann, ohne den Kontext jedes Mal neu zu erklären.*

**Akzeptanzkriterien:**
- ✓ Vorherige Fragen und Antworten der Sitzung (max. 3 Frage-Antwort-Paare) fliessen als Kontext in Folgefragen ein.
- ✓ Die Gesprächshistorie der Session ist für Lara sichtbar (Scroll-Verlauf).
- ✓ Lara kann jederzeit eine neue Konversation starten (Context reset).
- ✓ Quellenverweise aus vorherigen Antworten bleiben in der Sitzung verlinkt.
- ✓ Die Gesprächshistorie ist nur für die aktive Browser-Session gültig; beim Schliessen des Browsers wird der Kontext verworfen.

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
- ✓ Stefan kann direkt aus dem Cluster-Detail einen Dokument-Upload oder eine Re-Validierung anstossen.

---

## MoSCoW-Legende

| MUST | SHOULD | COULD |
|------|--------|-------|
| Muss umgesetzt werden | Sollte umgesetzt werden | Kann umgesetzt werden |

---

*Quellen: LearnFlow_UserStories_v2.md · Überarbeitung nach RE-Review Mai 2026*
*Änderungsstand: v3 — 2026-05-20*
