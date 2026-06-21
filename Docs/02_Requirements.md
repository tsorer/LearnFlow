# LearnFlow — Requirements Document v1
*Product Owner · Mai 2026*

---

## 1. Projektzusammenfassung

LearnFlow ist eine interne Lernplattform, die neuen Mitarbeitenden erlaubt, Fragen zu fachlichen Prozessen in natürlicher Sprache zu stellen und quellenbelegte Antworten aus einem kuratierten Wissenskorpus zu erhalten. Das Problem: Domänenwissen steckt in den Köpfen erfahrener Kolleg:innen und in verstreuten, schlecht gepflegten Dokumenten — neue Mitarbeitende werden nicht produktiv, Wissensträger werden täglich unterbrochen. Das MVP liefert einen lauffähigen Piloten für einen einzigen Bereich bis 30. September 2026 — kein Vollprodukt, sondern ein validiertes Fundament.

---

## 2. Personas

### Lara — Lernende

| | |
|---|---|
| **Job** | Junior Developer, erste Wochen im Unternehmen |
| **Problem** | Fachprozesse und historisch gewachsene Systeme sind nicht verständlich dokumentiert; das Wissen steckt bei erfahrenen Kolleg:innen |
| **Ziel** | Eigenständig Antworten zu Domänenfragen finden, ohne jedes Mal jemanden zu unterbrechen — und der Antwort vertrauen können |

### Stefan — Bereichsverantwortlicher

| | |
|---|---|
| **Job** | Senior-Mitarbeitender, fachlich verantwortlich für einen Bereich, Knowledge Owner |
| **Problem** | Neue Mitarbeitende stellen dieselben Fragen immer wieder; Dokumentation ist verstreut, veraltet, aufwändig zu pflegen |
| **Ziel** | Wissen einmalig aufbereiten und dauerhaft zugänglich halten, ohne täglich als Auskunftsperson gebraucht zu werden |

---

## 3. MVP-Constraints

| Constraint | Wert |
|---|---|
| Anzahl Bereiche | 1 (Pilot-Bereich, hartcodiert) |
| User-Management | DB-Script — kein Admin-UI; Felder: email, passwort, Rolle |
| Authentifizierung | E-Mail / Passwort (lokal); post-MVP SSO via IdP (E-Mail als Identifier für Azure AD / SAML) |
| Rollen | Lernende / Bereichsverantwortlicher / Admin |
| Budget | 480 h gesamt (4 Personen × 15 Wochen × 1 Tag/Woche), davon **360 h Umsetzung** und ~120 h Planung/Analyse/Architektur |
| Deadline | 30. September 2026 |

---

## 4. User Stories

### US-01 · Quellenbelegte Frage-Antwort

**Persona:** Lara

*Als Lernende möchte ich eine Frage in natürlicher Sprache stellen und eine quellenbelegte Antwort erhalten, damit ich Fachprozesse verstehen kann, ohne erfahrene Kolleg:innen zu unterbrechen.*

**Akzeptanzkriterien:**
- ✓ Jede Antwort enthält mindestens einen klickbaren Quellenverweis (Dokumenttitel + Abschnitt + Upload-Datum).
- ✓ Ein Klick auf eine Quellenangabe öffnet das Originaldokument und hebt den belegenden Abschnitt visuell hervor.
- ✓ Antworten ohne identifizierbare Quelle werden nicht angezeigt.
- ✓ Eingaben unter 3 Zeichen oder über 1.000 Zeichen werden clientseitig abgewiesen mit einem verständlichen Hinweis.
- ✓ Ist der LLM- oder Retrieval-Service nicht erreichbar, erscheint eine klare Fehlermeldung — keine erfundene Antwort.
- ✓ Antwortzeit im 95. Perzentil maximal 10 Sekunden.

---

### US-02 · Unsichere Antworten erkennen

**Persona:** Lara

*Als Lernende möchte ich klar erkennen, wenn das System sich seiner Antwort nicht sicher ist, damit ich keinen halluzinierten Inhalten vertraue.*

**Akzeptanzkriterien:**
- ✓ Unterschreitet der Konfidenz-Score einen konfigurierten Schwellenwert, zeigt das System: „Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden."
- ✓ Nach „Ich weiss es nicht" gibt das System einen Hinweis zur Präzisierung (z. B. „Versuche, einen konkreten Prozess oder ein Dokument zu nennen").
- ✓ Liegt der Anteil belegter Aussagen im Self-Check unter 80 %, wird die Antwort als „Eingeschränkt belegt" markiert (Farbe + Icon + Hinweistext).
- ✓ Liegt der Anteil unter 50 %, wird die Antwort vollständig unterdrückt.
- ✓ Der Konfidenz-Score ist in der Antwort-Metainfo einsehbar.
- ✓ Schwellenwert ist per DB-Script oder Admin-Seite (US-11) änderbar — kein Code-Deployment erforderlich.
- ✓ Das System gibt bei Out-of-Corpus-Testfragen in mindestens 90 % der Fälle „Weiss ich nicht" zurück.

> **Entscheid 2026-05-20:** Vorrang-Reihenfolge: (1) Quellenprüfung (US-01) — keine identifizierbare Quelle → Antwort wird nicht angezeigt. (2) Konfidenz-Score-Schwellenwert — Score zu tief → „Ich weiss es nicht". (3) Self-Check-Anteil — unter 80 % → „Eingeschränkt belegt"; unter 50 % → unterdrückt.

---

### US-03 · Feedback zu Antworten geben

**Persona:** Lara

*Als Lernende möchte ich jede Antwort als hilfreich oder nicht hilfreich markieren und einen Grund angeben, damit unklare oder falsche Antworten erkannt werden können.*

**Akzeptanzkriterien:**
- ✓ Jede Antwort enthält eine Bewertungsmöglichkeit (👍 / 👎).
- ✓ Bei 👍: Kategorie wählen — verständlich / vollständig / hilfreich für Code / Quelle passt gut.
- ✓ Bei 👎: Kategorie wählen — faktisch falsch / unvollständig / veraltet / unverständlich / Quelle stimmt nicht.
- ✓ Optional: Freitext-Ergänzung bei beiden Varianten.
- ✓ Nach dem Speichern: Bestätigung für Lara; Feedback erscheint im Dashboard von Stefan.
- ✓ Feedback wird pseudonymisiert erfasst — keine Rückverfolgung auf einzelne Lernende.

---

### US-04 · Inhalte in den Lernkorpus aufnehmen

**Persona:** Stefan

*Als Bereichsverantwortlicher möchte ich Dokumente in den Lernkorpus meines Bereichs aufnehmen können, damit nur von mir verwaltete Inhalte als Wissensgrundlage für KI-Antworten dienen.*

**Akzeptanzkriterien:**
- ✓ Upload in den Formaten PDF, Word (.docx) und Markdown.
- ✓ Dokumente bis 50 Seiten / 10 MB sind nach maximal 5 Minuten als Quelle verfügbar.
- ✓ Maximale Dateigrösse: **10 MB** (hartes Limit, serverseitig); Dateien über 10 MB werden mit einer Fehlermeldung abgewiesen. *(Entscheid 2026-06-10, konsistent mit ADR-003: `bytea`-Ablage; grössere Dateien sind kein MVP-Scope.)*
- ✓ Alle hochgeladenen Dokumente zeigen eine Fortschrittsanzeige während der Verarbeitung.
- ✓ Eine neue Version (gleicher Dateiname) ersetzt automatisch das bestehende Dokument.
- ✓ Stefan kann ein Dokument jederzeit löschen.
- ✓ Hochgeladene Dokumente erhalten einen Zeitstempel, der für Lara sichtbar ist.
- ✓ Nur Dokumente des eigenen Bereichs sind sichtbar und verwaltbar.

---

### US-05 · Authentifizierung und Bereichszuordnung

**Persona:** Lara & Stefan

*Als Plattformnutzer:in möchte ich mich sicher anmelden und automatisch den Bereich sehen, dem ich zugeordnet bin, damit nur autorisierte Mitarbeitende Zugang haben.*

**Akzeptanzkriterien:**
- ✓ Authentifizierung per E-Mail/Passwort; Accounts per DB-Script angelegt (Felder: email, passwort, Rolle: Lernende / Bereichsverantwortlicher / Admin) — keine Self-Service-Registrierung.
- ✓ Post-MVP: SSO-Anbindung via Unternehmens-IdP (z. B. Azure AD / SAML 2.0).
- ✓ Nicht authentifizierte Nutzer werden auf die Login-Seite weitergeleitet.
- ✓ Nach dem Login sieht jede Person den Pilot-Bereich (hartcodiert).
- ✓ Rollen werden beim Account-Anlegen gesetzt; post-MVP aus dem IdP übernommen.

---

### US-06 · Veraltete Inhalte erkennen und re-validieren

**Persona:** Stefan

*Als Bereichsverantwortlicher möchte ich eine Übersicht über veraltete Inhalte erhalten und diese aktiv re-validieren können, damit der Lernkorpus stets aktuell bleibt.*

**Akzeptanzkriterien:**
- ✓ Dashboard zeigt alle Dokumente, die seit mehr als 90 Tagen nicht re-validiert wurden, sortiert nach Alter.
- ✓ Stefan kann einen Eintrag als „aktuell", „ersetzt durch …" oder „entfernen" markieren.
- ✓ Stale-Schwellenwert (Standard: 90 Tage) ist per DB-Script oder Admin-Seite (US-11) änderbar.

> **Entscheid 2026-05-20:** Die Stale-Uhr wird zurückgesetzt durch (a) Upload eines Dokuments und (b) explizite Re-Validierung per Klick im Dashboard.

---

### US-07 · KI-generierte Quiz-Fragen prüfen und freigeben

**Persona:** Stefan

*Als Bereichsverantwortlicher möchte ich vom LLM vorgeschlagene Multiple-Choice-Fragen prüfen und freigeben oder ablehnen, damit nur validierte Quizfragen verwendet werden.*

**Akzeptanzkriterien:**
- ✓ Stefan löst die Quiz-Generierung manuell per Klick aus.
- ✓ Review-Dashboard zeigt alle nicht freigegebenen Fragen inklusive Quellen-Passage.
- ✓ Fragen können einzeln freigegeben, abgelehnt oder editiert werden.
- ✓ Abgelehnte Fragen sind für Lernende nicht sichtbar.
- ✓ Freigegebene Fragen erhalten einen Zeitstempel.

**Abhängigkeit:** US-04

---

### US-08 · Quiz absolvieren

**Persona:** Lara

*Als Lernende möchte ich zu einem Thema ein kurzes Quiz absolvieren, damit ich überprüfen kann, ob ich das Gelesene wirklich verstanden habe.*

**Akzeptanzkriterien:**
- ✓ Quiz mit 5 Multiple-Choice-Fragen aus dem Pool freigegebener Quizfragen pro Bereich.
- ✓ Sind keine Quizfragen freigegeben: Button sichtbar mit Hinweis „Es sind noch keine Quizfragen für diesen Bereich freigegeben."
- ✓ Nach Abschluss: pro Frage richtig/falsch, korrekte Antwort mit Erklärung und Direktlink zur belegenden Quelle.
- ✓ Quiz-Ergebnisse werden nicht personenbezogen gespeichert.

**Abhängigkeit:** US-07

---

### US-09 · Folgefragen im Gesprächskontext

**Persona:** Lara

*Als Lernende möchte ich nach einer Antwort Folgefragen im gleichen Kontext stellen können, damit ich ein Thema schrittweise vertiefen kann.*

**Akzeptanzkriterien:**
- ✓ Max. 3 vorherige Frage-Antwort-Paare fliessen als Kontext in Folgefragen ein.
- ✓ Gesprächshistorie der Session ist für Lara sichtbar (Scroll-Verlauf).
- ✓ Lara kann jederzeit eine neue Konversation starten (Context reset).
- ✓ Gesprächshistorie gilt nur für die aktive Browser-Session; beim Schliessen des Browsers verworfen.

---

### US-10 · Wissens-Lücken im Bereich erkennen

**Persona:** Stefan

*Als Bereichsverantwortlicher möchte ich sehen, welche Fragen häufig gestellt werden oder oft negatives Feedback erhalten, damit ich gezielt Dokumentation ergänzen kann.*

**Akzeptanzkriterien:**
- ✓ Dashboard zeigt Top-10-Themen-Cluster (Embedding-Ähnlichkeit) mit Häufigkeit und aggregierter Feedback-Quote — sobald konfigurierter Schwellenwert erreicht (Standard: 30 Tage / mind. 20 Fragen).
- ✓ Cluster mit weniger als 5 Fragen werden nicht angezeigt (Datenschutz).
- ✓ Klick auf Cluster zeigt Beispielfragen und verwendete Quellen.
- ✓ Direkt aus dem Cluster-Detail: Upload oder Re-Validierung anstossen.

---

### US-11 · Systemkonfiguration über Admin-Seite

**Persona:** Admin

*Als Admin möchte ich Systemparameter über eine geschützte Seite anpassen können, damit ich Konfidenz- und Stale-Schwellenwerte ohne Code-Deployment ändern kann.*

**Akzeptanzkriterien:**
- ✓ Konfidenz-Schwellenwert (US-02) und Stale-Schwellenwert (US-06) über Admin-Seite anpassbar; Änderungen wirken sofort ohne Neustart.
- ✓ Beide Werte alternativ per DB-Script änderbar (Fallback).
- ✓ Konfigurationsänderungen werden mit Zeitstempel und ausführender Person protokolliert.
- ✓ Admin-Seite nur für Admin-Rolle erreichbar; direkter URL-Aufruf ohne Admin-Rechte wird abgewiesen.

---

## 5. MoSCoW-Tabelle

| Story | Titel | Priorität | Begründung |
|---|---|---|---|
| US-01 | Quellenbelegte Frage-Antwort | **MUST** | Kernfunktion; ohne quellenbelegte Antworten ist das Vertrauensversprechen nicht einlösbar |
| US-02 | Unsichere Antworten erkennen | **MUST** | Eine falsch dargestellte Antwort ist schlimmer als gar keine — Fundament des Nutzervertrauens |
| US-03 | Feedback zu Antworten | **MUST** | Ohne Feedback-Loop keine Grundlage für Qualitätskontrolle oder Verbesserungen |
| US-04 | Inhalte aufnehmen | **MUST** | Ohne Korpus-Verwaltung keine Wissensbasis — Voraussetzung für alle anderen Stories |
| US-05 | Authentifizierung | **MUST** | Interne Dokumente ohne Zugangskontrolle sind nicht akzeptabel |
| US-06 | Veraltete Inhalte erkennen | **SHOULD** | Wichtig für langfristige Qualität, aber Pilot kann ohne starten |
| US-07 | Quiz-Fragen prüfen | **SHOULD** | Differenzierendes Feature; für Day-1-Nutzwert nicht blockierend |
| US-08 | Quiz absolvieren | **SHOULD** | Lernpädagogisch wertvoll; setzt US-07 voraus und ist im MVP nicht kritisch |
| US-11 | Systemkonfiguration Admin | **SHOULD** | DB-Script-Fallback vorhanden; Admin-UI ist Komfort, kein Blocker |
| US-09 | Folgefragen im Kontext | **COULD** | Verbessert UX erheblich, erhöht aber Komplexität (Token-Management, Kosten) |
| US-10 | Wissenslücken erkennen | **COULD** | Braucht ausreichend Nutzungsdaten; im Pilotbetrieb noch nicht sinnvoll |

---

## 6. Top 3 Risiken — Vor Implementierungsstart klären

### Risiko 1 · RAG-Qualität ist nicht garantierbar

Das Kernversprechen — verlässliche, quellenbelegte Antworten — hängt an einem Mechanismus (Retrieval + LLM), dessen Qualität stark von Chunking-Strategie, Embedding-Modell und Prompt-Design abhängt. Halluzinationen mit echter Quellenangabe sind technisch möglich. Ein technischer Spike mit echten Dokumenten und echten Testfragen muss **vor** Implementierungsbeginn zeigen, ob das Qualitätsniveau erreichbar ist.

**Was zu klären ist:** Evaluationsdataset definieren, Qualitätsschwelle festlegen, Spike-Ergebnis als Go/No-Go-Entscheidung behandeln.

### Risiko 2 · Konfidenz-Scoring ist undefiniert

US-02 enthält zwei verschiedene Unterdrückungsmechanismen (Konfidenz-Score vs. Anteil belegter Aussagen im Self-Check) die nicht reconciliert sind, plus einen dritten aus US-01 (keine identifizierbare Quelle). Welcher hat Vorrang? Was ist der Self-Check konkret — LLM-Selbstevaluation, semantische Ähnlichkeit zwischen Antwort und Chunks? Diese Frage ist keine Detail-Entscheidung, sie ist die Implementierung des Kernfeatures.

**Was zu klären ist:** Einen einzigen, definierten Mechanismus festlegen und die drei AC in US-01/US-02 darauf ausrichten.

### Risiko 3 · Externe Abhängigkeiten blockieren zum falschen Zeitpunkt

~~Zwei ungelöste externe Abhängigkeiten~~ — **Stand Sprint 0 (2026-05-27): beide Punkte entschieden.**

**(a) LLM-API-Quota — ✅ entschieden:** Stack ist OpenAI API (api.openai.com). Kein Quota-Genehmigungsprozess nötig — sofort verfügbar mit API-Key. Lokaler Fallback via Ollama für datenschutzkritische Umgebungen (ADR-004).

**(b) E-Mail-Service für US-06 — ✅ entschieden:** E-Mail ist nicht im Scope. US-06 (Stale-Content-Erkennung) bleibt im Dashboard; kein automatischer E-Mail-Report.

> Risiko 3 ist damit aufgelöst. Verbleibende externe Abhängigkeit: Unternehmens-IdP für Post-MVP SSO — nicht zeitkritisch für Sprint 1.

---

## 7. Out of Scope — Won't Have im MVP

| Feature | Begründung |
|---|---|
| SSO / IdP-Anbindung | Zu komplex für MVP; post-MVP explizit geplant (US-05) |
| Mehr als 1 Bereich | Hartcodierter Pilot; Multi-Bereich erfordert vollständiges RBAC-Redesign |
| Passwort-Reset UI | Kein Admin-UI für User-Management; Reset per DB-Script durch Admin |
| Self-Service-Registrierung | Accounts nur per DB-Script; offene Registrierung ist Sicherheitsrisiko |
| Audit-Log für Dokument-Operationen | Wer hat was hochgeladen/gelöscht — relevant für Compliance, aber kein MVP-Blocker |
| Mehrsprachigkeit | Nur Deutsch im MVP; Dokumente in anderen Sprachen (EN, FR) nicht adressiert |
| DSGVO-Löschantrag-Workflow | Aufbewahrungsfristen für Query-Logs und Feedback-Freitext nicht definiert — Post-MVP |
| Diff-Ansicht bei Dokumenten-Updates | Stefan sieht geänderte Abschnitte beim Re-Upload — explizit als Post-MVP markiert (US-06) |
| Mobile / responsive UI | Nicht spezifiziert; Desktop-Browser als einziges Target |

---

*Quellen: LearnFlow_UserStories_v3.md · RE-Review und Risikoanalyse Mai 2026*
*Stand: v1 — 2026-05-20*
