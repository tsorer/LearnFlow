# LearnFlow – Realistischer Plan (15 Wochen, Ferien eingerechnet)

**Datum:** 3. Mai 2026
**Annahmen:** 3 Personen, 15 effektive Arbeitswochen (Ferien bereits abgezogen), 8 h/Person/Woche

---

## Verfügbares Budget

| Größe | Wert |
|---|---|
| Personen | 3 |
| Effektive Wochen | 15 |
| Stunden/Person/Woche | 8 |
| **Gesamtbudget** | **360 Personenstunden** |

> Das ist deutlich weniger als die 500–1.000 h aus der ersten Schätzung. Konsequenz: **echter Scope-Schnitt nötig** – Quiz kommt komplett raus, Stories werden auf Walking-Skeleton-Niveau implementiert.

---

## Verdikt

**Machbar – aber nur, wenn der Scope auf den Q&A-Kern reduziert wird.** Quiz, Admin-UI, echte Authentifizierung und alle „Pflege-Features" entfallen im Prototyp und werden nur konzeptionell beschrieben. Was am Ende läuft, ist ein **Q&A-Proof-of-Concept** für *einen* Bereich mit hartcodiertem Korpus.

---

## Aufwandsschätzung (Re-Plan)

| Block | Aufwand | Was es enthält |
|---|---:|---|
| **Sprint 0 – Tech-Spike & Setup** | 50 h | Architekturentscheidungen, LLM-API anbinden (Azure OpenAI EU), Vector-DB aufsetzen, Repo + CI, RAG-Prototyp auf 5 Demo-Dokumenten |
| **Story 1 – Q&A mit Quellen** | 90 h | Backend (Retrieval, Prompt, Generierung), Chat-UI, Quellenanzeige mit Highlighting, Error-Handling |
| **Story 4 – Unsicherheit / „Weiß ich nicht"** | 40 h | Konfidenz-Schwellwert, Self-Check-Pass des Modells, Markierung „Eingeschränkt belegt", 90%-Test mit Out-of-Corpus-Fragen |
| **Story 2 minimal – Korpus aufnehmen** | 30 h | CLI/Skript für Bulk-Upload, einfache Status-Seite (ohne UI-Politur), keine richtige Pflege-UX |
| **Story 3 – Feedback-Schleife** | 25 h | 👍/👎 + Kategorien, Speicherung, einfache Liste fürs Bereichs-Dashboard |
| **Polish, kleine UI-Iterationen, Testing** | 50 h | Typo-Fixes, Layout, manuelle Tests, Bug-Bashes |
| **Doku, Präsentationsvorbereitung, Demo** | 45 h | Konzept-Doku für nicht-implementierte Features (Quiz, Admin, Auth, Stale-Content), Pitch-Deck, Demo-Video, Live-Demo proben |
| **Puffer** | 30 h | Krankheit, Lernkurve, technische Überraschungen |
| **Summe** | **360 h** | exakt im Budget, kein Spielraum nach oben |

---

## Was im MVP **drin** ist

✅ Story 1 – Frage stellen, quellenbelegte Antwort bekommen
✅ Story 2 (minimal) – Korpus über Skript befüllen + Status-Seite
✅ Story 3 – Feedback geben (👍/👎 + Kategorie)
✅ Story 4 – Unsichere Antworten markieren + „Weiß ich nicht"

→ Das ist der **echte Q&A-Loop**. Beweist die Kern-Hypothese „RAG auf unseren Inhalten liefert belegbar nützliche Antworten" inkl. Vertrauensmechanik.

## Was im MVP **draußen** ist (nur als Konzept dokumentiert)

❌ Story 5 – Stale-Content-Erkennung
❌ Story 6a / 6b – Quiz absolvieren / Quiz-Freigabe
❌ Story 7 – Wissens-Lücken-Dashboard
❌ Story 8 – Echte SSO-Authentifizierung *(hartcodierter Demo-User)*
❌ Story 9 – Bereichs-/Admin-Verwaltung *(ein Bereich, hartcodiert)*
❌ Story 10 – Folgefragen mit Konversationskontext
❌ Story 11 – Kaputte Quellen erkennen

> **Wichtig fürs Storytelling im Pitch:** Diese Features stehen **konzeptionell ausgearbeitet** im Backlog – das beweist, dass das Team die Tiefe verstanden hat. Sie sind bewusst nicht implementiert, weil 360 h für mehr nicht reichen.

---

## Wochenplan (15 effektive Wochen)

| Woche | Phase | Wer macht was | Meilenstein |
|---:|---|---|---|
| **W 1** | Tech-Spike | Alle 3: Workshop, Stack-Entscheidung, Repo-Setup | Stack fixiert (Azure OpenAI EU, Vector-DB X, Frontend Y) |
| **W 2** | Setup | Person A: Backend-Skeleton, Person B: Frontend-Skeleton, Person C: erste 5 Demo-Dokumente kuratieren | Erstes „Hello World"-RAG-Antwort auf Demo-Frage |
| **W 3–4** | Story 1 Backend | Person A: Retrieval + Prompt + Generierung. Person B: Chat-UI. Person C: Korpus-Pipeline | Chat-UI sendet Frage an Backend, bekommt Antwort zurück |
| **W 5** | Story 1 Quellen | Person A+B: Quellenanzeige + Highlighting umsetzen | Antwort kommt mit klickbaren Quellen, Highlight-Scrolling |
| **W 6** | Story 4 | Person A: Konfidenz-Schwellwert + Self-Check. Person C: Out-of-Corpus-Testset bauen | „Weiß ich nicht" funktioniert in 90% der Testfälle |
| **W 7** | Story 2 minimal | Person B: CLI-Upload-Skript + Status-Seite. Person C: 30 echte Pilot-Bereich-Dokumente einspielen | Echter Korpus läuft mit echten Dokumenten |
| **W 8** | **MVP-Review #1** | Alle 3: Lara-Fragen-Sammlung sammeln (5–10 echte), erstmal selber testen | Erste echte Antworten auf echte Fragen, Probleme sichtbar |
| **W 9** | Story 3 Feedback | Person A: 👍/👎 + Kategorien-Backend. Person B: Feedback-UI + simpler Dashboard-View | Feedback wird gespeichert und ist sichtbar |
| **W 10** | Iteration auf Feedback | Alle 3: Top-3 Probleme aus W8 beheben (Prompt-Tuning, Retrieval-Verbesserungen) | Antwort-Qualität messbar besser |
| **W 11** | Polish & Testing | Person A+B: Bug-Fixing, Layout. Person C: konzeptionelle Doku der nicht-implementierten Features | Alles, was implementiert ist, funktioniert sauber |
| **W 12** | **MVP-Review #2 mit echten Lara-Fragen** | Alle 3: Demo vor 1–2 echten Junior-Devs, Feedback einsammeln | Belegt, ob das Tool tatsächlich hilft |
| **W 13** | Letzte Iteration | Schwerpunkt auf gröbste W12-Findings | Demo-tauglich, ohne peinliche Bugs |
| **W 14** | Doku & Pitch | Alle 3: Abschluss-Doku, Pitch-Deck, Demo-Video aufnehmen | Doku komplett, Pitch geprobt |
| **W 15** | **Puffer + Präsentation** | Reservezeit, finale Vorbereitung | Abgabe / Präsentation am 30. September |

---

## Drei kritische Bedingungen (gleich wie zuvor, aber wichtiger denn je)

1. **Tech-Stack in Woche 1 fixiert.** Bei 360 h ist kein Tag für „nochmal überlegen" da. Bevorzugt Azure OpenAI EU (kein On-Prem-Abenteuer).
2. **Pilot-Bereich + ~30 Dokumente bis Ende Woche 2.** Sonst keine echten Testdaten = Demo auf Papier.
3. **Strenge Scope-Disziplin – das ist kein Vorschlag, sondern Pflicht.** Jeder „kleine Wunsch" eines Stakeholders kostet bei diesem Budget eine andere Story den Platz. Ein dokumentiertes „nein, nicht im MVP" pro Woche.

---

## Was bei Abweichungen passiert

**Wenn eine Person eine Woche krank wird:** Verlust ~8 h, frisst den Puffer um ein Drittel. Noch zu schaffen, aber kein Polish.

**Wenn der Tech-Spike länger dauert (W1 → W3):** kritisch. Story 1 wird nicht in W5 fertig, Verschiebung kaskadiert. Mitigation: in W4 entscheiden, ob auf Story 4 (Unsicherheit) verzichtet wird.

**Wenn der Pilot-Bereich erst in W4 steht:** Demo-Dokumente länger nutzen, echter Korpus erst in W9. Riskant für die zweite MVP-Review.

**Wenn das Team RAG noch nicht kennt:** +50–80 h Lernkurve. Bei 360 h Budget = nicht abfangbar. Konsequenz: weiteres Story raus (z.B. Story 3 Feedback) oder Quiz-Konzept-Doku verkürzen.

---

## Empfehlung fürs Pitch-Storytelling

Bei diesem Scope ändert sich die Erzählung leicht:

**Vorher (üppiges Budget):** „Wir bauen einen Walking-Skeleton-MVP mit Quiz."

**Jetzt (360 h):** „Wir liefern einen **Q&A-Proof-of-Concept**, der die zentrale Hypothese belegt – RAG auf kuratiertem Bereichs-Korpus + sichtbare Quellen + ehrliches ‚Weiß ich nicht' = vertrauenswürdige Antworten. Quiz, Admin, Auth und Pflege-Features sind **konzeptionell ausgearbeitet im Backlog**, nicht implementiert. Wir zeigen, dass wir die Komplexität verstanden haben, statt halbgar in alle Richtungen zu bauen."

Das ist im Kurs-Kontext **ehrlicher** und für die Zuhörer:innen **glaubwürdiger** als ein „MVP" zu versprechen, der dann nicht hält.

---

## Was du als PO jetzt entscheiden musst

1. **Scope OK?** Bist du bereit, Quiz im Prototyp zu opfern?
2. **Pilot-Bereich:** Wer wird es konkret? Wann gibst du Bescheid? *(blockt W2)*
3. **Tech-Stack-Workshop:** Wann findet er statt? *(blockt W1)*
4. **Wer ist „Person A/B/C"?** Skill-Mapping (wer macht Backend, wer Frontend, wer Domain/Doku)?
5. **Echte Lara:** Hast du 1–2 Junior-Entwickler:innen, die in W8 und W12 zum Testen verfügbar sind?

Antworten auf diese fünf Fragen sind die echten „nächsten Schritte" der Woche 1.
