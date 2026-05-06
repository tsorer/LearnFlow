# LearnFlow – Kritische User Stories

> 5 User Stories zu bisher ungeklärten technischen und organisatorischen Fragen,
> die typischerweise später zu Problemen führen.

---

## Story A – Retrieval-Kalibrierung

**Kritische Frage:** Wie werden Chunk-Grösse und Unsicherheits-Schwellwert definiert und validiert?

**Story:**
Als **Entwickler:in im LearnFlow-Team** möchte ich einen konfigurierbaren Unsicherheits-Schwellwert für das Retrieval definieren und anhand eines Testsets validieren können, damit das System konsistent und nachvollziehbar zwischen „weiss ich" und „weiss ich nicht" unterscheidet.

**Acceptance Criteria:**

- **AC1:** Given ein Testset mit 20 bekannten Out-of-Corpus-Fragen existiert, When der Schwellwert konfiguriert ist, Then gibt das System bei mindestens 18 dieser Fragen ein „Weiss ich nicht" zurück (≥ 90 %).
- **AC2:** Given der Schwellwert wird im Admin-Panel geändert, When die Änderung gespeichert wird, Then gilt sie für alle nachfolgenden Anfragen ohne Neustart des Systems.

---

## Story B – Datenschutzkonforme Fragespeicherung

**Kritische Frage:** Was darf von den Nutzeranfragen gespeichert, wie lange behalten und wer darf es einsehen?

**Story:**
Als **Datenschutzbeauftragte:r** möchte ich konfigurieren können, ob und wie lange Fragen von Nutzer:innen gespeichert werden und wer Zugriff darauf hat, damit die Plattform DSGVO-konform betrieben werden kann.

**Acceptance Criteria:**

- **AC1:** Given eine Frage wurde gestellt, When sie verarbeitet ist, Then wird sie entweder gar nicht persistiert oder ausschliesslich pseudonymisiert (kein Klarnamen-Bezug) und nur für den definierten Aufbewahrungszeitraum gespeichert.
- **AC2:** Given die Aufbewahrungsfrist ist abgelaufen, When der nächtliche Bereinigungsjob läuft, Then sind die betroffenen Datensätze unwiderruflich gelöscht und ein Löschprotokoll ist im Audit-Log einsehbar.

---

## Story C – LLM-Anbindung und Failover

**Kritische Frage:** Wer gibt die LLM-Freigabe, und was passiert bei einem Ausfall des Endpoints?

**Story:**
Als **Systemadministrator:in** möchte ich den verwendeten LLM-Endpoint zentral konfigurieren und bei einem Ausfall auf einen Fallback-Endpoint umschalten können, damit ein Anbieter-Wechsel oder ein temporärer Ausfall die Plattform nicht lahmlegt.

**Acceptance Criteria:**

- **AC1:** Given der primäre LLM-Endpoint antwortet nicht innerhalb von 15 Sekunden, When das System einen Retry durchführt, Then wird nach 2 Fehlversuchen automatisch auf den konfigurierten Fallback-Endpoint gewechselt und ein Alert ausgelöst.
- **AC2:** Given ein neuer LLM-Endpoint wird in der Konfiguration hinterlegt, When ein Test-Request abgesetzt wird, Then gibt das System eine Bestätigung „Verbindung erfolgreich" und die durchschnittliche Latenz aus – ohne Neudeployment.

---

## Story D – Bereichsübergreifende Suchanfragen

**Kritische Frage:** Was passiert, wenn eine Frage bereichsübergreifend beantwortet werden könnte?

**Story:**
Als **Lara** möchte ich erfahren, wenn meine Frage in einem anderen Bereich besser beantwortet werden könnte, damit ich nicht mit einer „Weiss ich nicht"-Antwort steckenbleibe, obwohl das Wissen im System vorhanden ist.

**Acceptance Criteria:**

- **AC1:** Given mein primärer Bereich hat keinen passenden Treffer (Similarity unter Schwellwert), When ein anderer Bereich einen Treffer über Schwellwert liefert, Then zeigt das System einen Hinweis „In Bereich [X] gibt es möglicherweise eine Antwort – möchtest du dort suchen?" ohne die Antwort automatisch anzuzeigen.
- **AC2:** Given Lara bestätigt die bereichsübergreifende Suche, When die Antwort angezeigt wird, Then ist klar ersichtlich aus welchem Bereich die Quelle stammt, und es wird kein Inhalt angezeigt, für den Laras Rolle keine Leserechte hat.

---

## Story E – Versionierung von Korpus-Dokumenten

**Kritische Frage:** Was passiert mit alten Chunks im Vektorindex, wenn ein Dokument aktualisiert wird?

**Story:**
Als **Stefan** möchte ich ein bereits im Korpus vorhandenes Dokument durch eine neue Version ersetzen können, damit veraltete Chunks automatisch ungültig werden und keine widersprüchlichen Antworten entstehen.

**Acceptance Criteria:**

- **AC1:** Given ich lade Dokument „Grundbedarf_v2.pdf" hoch und im Korpus existiert bereits „Grundbedarf_v1.pdf", When das neue Dokument verarbeitet ist, Then werden alle Chunks der Vorgängerversion aus dem Vektorindex entfernt und nur Chunks aus v2 für Antworten verwendet.
- **AC2:** Given eine Vorgänger-Version wurde ersetzt, When Stefan das Korpus-Dashboard öffnet, Then sieht er einen Eintrag im Versions-Log mit Datum, ersetztem Dokument und Anzahl entfernter Chunks.
