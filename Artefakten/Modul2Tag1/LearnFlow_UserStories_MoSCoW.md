# LearnFlow
## User Stories – MoSCoW-Priorisierung
*Rolle: Requirements Engineer · KI-gestützte Lernplattform für neue Mitarbeitende · Mai 2026*

---

## MUST – Muss umgesetzt werden

### US-01 · Quellenbelegte Antworten anzeigen

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich zu jeder KI-Antwort mindestens einen klickbaren Quellenverweis sehen, damit ich die Aussage selbst nachvollziehen und mich auf korrekte Informationen verlassen kann.*

**Akzeptanzkriterien:**
- ✓ Jede Antwort enthält mindestens einen klickbaren Quellenverweis.
- ✓ Der Verweis zeigt Dokumenttitel, Abschnitt und Validierungsdatum an.
- ✓ Ein Klick öffnet das Quelldokument an der entsprechenden Stelle.
- ✓ Antworten ohne identifizierbare Quelle werden nicht angezeigt.

---

### US-02 · Unsichere Antworten klar kennzeichnen

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich, dass das System bei niedriger Konfidenz explizit „Ich weiß es nicht" anzeigt, anstatt zu raten, damit ich keine falschen Informationen unbemerkt übernehme.*

**Akzeptanzkriterien:**
- ✓ Unterschreitet der Konfidenz-Score einen definierten Schwellenwert, erscheint eine sichtbare Warnung.
- ✓ Statt einer unsicheren Antwort zeigt das System eine klare Meldung: „Ich weiß es nicht".
- ✓ Das System schlägt nach Anzeige von „Ich weiß es nicht" eine Reformulierung der Frage vor.
- ✓ Der Konfidenz-Score ist in der Antwort-Metainfo einsehbar.
- ✓ Der initiale Schwellenwert wird im Pilotbetrieb empirisch ermittelt; danach ist er über das Admin-Setting konfigurierbar.

---

### US-03 · Korpus hochladen und für Bereich freigeben

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich Dokumente in die Plattform hochladen und für meinen Fachbereich freigeben können, damit nur von mir geprüfte Inhalte als Wissensgrundlage für KI-Antworten dienen.*

**Akzeptanzkriterien:**
- ✓ Stefan kann Dokumente (PDF, Word, Confluence-Export) hochladen.
- ✓ Hochgeladene Dokumente sind erst nach expliziter Freigabe durch Stefan aktiv.
- ✓ Stefan kann die Freigabe jederzeit widerrufen.
- ✓ Lädt Stefan ein bereits freigegebenes Dokument in neuer Version hoch, wird die neue Version sofort aktiv – kein erneuter Freigabeschritt erforderlich.
- ✓ Freigegebene Dokumente erhalten einen Zeitstempel, der für Lara sichtbar ist.
- ✓ Nur Dokumente des eigenen Bereichs sind sichtbar und freigabefähig.

---

## SHOULD – Sollte umgesetzt werden

### US-04 · Sicherer Login für alle Nutzer

**Persona:** Lara & Stefan – alle Nutzer

**User Story:**
*Als Plattformnutzerin möchte ich mich sicher anmelden können, damit nur autorisierte Mitarbeitende Zugang zur Plattform haben. Im MVP erfolgt dies per Username/Passwort; SSO-Anbindung (IdP) ist post-MVP geplant.*

**Akzeptanzkriterien:**
- ✓ MVP: Authentifizierung per Username/Passwort (lokal verwaltete Accounts).
- ✓ Post-MVP: SSO-Anbindung via Unternehmens-IdP (z. B. Azure AD / SAML 2.0) geplant.
- ✓ Nicht authentifizierte Nutzer werden auf die Login-Seite weitergeleitet.
- ✓ Rollen (Lernende / Bereichsverantwortliche) werden manuell beim Account-Setup zugewiesen (MVP); post-MVP aus dem IdP übernommen.

---

### US-05 · Monatlicher Stale-Content-Report

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich monatlich einen automatischen Report über veraltete oder lange nicht validierte Inhalte erhalten, damit ich die Aktualität des Lernkorpus proaktiv sicherstellen kann.*

**Akzeptanzkriterien:**
- ✓ Der Report wird automatisch einmal pro Monat per E-Mail versandt.
- ✓ Er listet alle Dokumente, die seit > 90 Tagen nicht validiert wurden.
- ✓ Jedes Dokument enthält einen Direktlink zur Freigabeoberfläche.
- ✓ Stefan kann den Schwellenwert (Tage bis „stale") selbst konfigurieren.

---

## COULD – Kann umgesetzt werden

### US-06 · Folgefragen im Gesprächskontext stellen

**Persona:** Lara – Junior Developer

**User Story:**
*Als Junior-Entwicklerin möchte ich nach einer Antwort Folgefragen im gleichen Kontext stellen können, damit ich ein Thema schrittweise vertiefen kann ohne jedes Mal von vorne anfangen zu müssen.*

**Akzeptanzkriterien:**
- ✓ Vorherige Fragen und Antworten der Sitzung fließen als Kontext in Folgefragen ein.
- ✓ Die Gesprächshistorie der Session ist für Lara sichtbar (Scroll-Verlauf).
- ✓ Lara kann jederzeit eine neue Konversation starten (Context reset).
- ✓ Quellenverweise aus vorherigen Antworten bleiben in der Sitzung verlinkt.
- ✓ Die Gesprächshistorie ist nur für die aktive Browser-Session gültig; beim Schließen des Browsers wird der Kontext verworfen.

---

### US-07 · KI-generierte Quiz-Fragen prüfen und freigeben

**Persona:** Stefan – Bereichsverantwortlicher

**User Story:**
*Als Bereichsverantwortlicher möchte ich vom LLM vorgeschlagene Multiple-Choice-Fragen prüfen und gezielt freigeben oder ablehnen, damit nur validierte Quiz-Fragen in der Lernkontrolle verwendet werden.*

**Akzeptanzkriterien:**
- ✓ Stefan löst die Quiz-Generierung manuell per Klick aus („Quiz generieren"-Schaltfläche); das System erstellt daraufhin Vorschläge aus den freigegebenen Dokumenten des Bereichs.
- ✓ Stefan sieht alle pending Fragen in einem Review-Dashboard.
- ✓ Er kann Fragen einzeln freigeben, ablehnen oder editieren.
- ✓ Abgelehnte Fragen werden nicht für Lernende sichtbar.
- ✓ Freigegebene Fragen erhalten einen Zeitstempel und sind Lara zugänglich.

---

## WON'T – Aktuell ausgeschlossen

### US-08 · Admin-Dashboard für Benutzer- und Bereichsverwaltung

**Persona:** IT-Administrator

**User Story:**
*Als IT-Administrator möchte ich Benutzer, Fachbereiche und Zugriffsrechte über ein zentrales Admin-Dashboard verwalten, damit die Plattform ohne direkten Datenbank-Zugriff administrierbar ist.*

**Akzeptanzkriterien:**
- ✓ CRUD-Operationen für Benutzer, Rollen und Bereiche über die UI.
- ✓ Audit-Log aller administrativen Aktionen.
- ✓ Bulk-Import von Nutzern via CSV.
- ✓ Nicht im MVP: wird erst nach erfolgreichem Pilot-Bereich adressiert.

---

## MoSCoW-Legende

| MUST | SHOULD | COULD | WON'T |
|------|--------|-------|-------|
| Muss umgesetzt werden | Sollte umgesetzt werden | Kann umgesetzt werden | Aktuell ausgeschlossen |
