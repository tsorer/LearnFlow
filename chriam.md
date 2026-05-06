<font color="cornflowerblue">
Du bist ein erfahrener Business Analyst. Wir entwickeln eine KI-gestützte Lernplattform für die fachliche Einarbeitung neuer Mitarbeiter:Innen in ein mittelgrosses Unternehmen der IT-Branche.

Zielgruppe: Neu angestellte Entwickler:innen; Requirement Engineers;

Zu lösendes Problem: Einarbeitungsprozess für neue Mitarbeiter:Innen ist langweilig. Er basiert grösstenteils auf schriftlichen Dokumenten. Die Dokumente sind zum Teil veraltet. Es besteht kein Prozess um die Dokumente und Informationen aktuell zu halten.

1.) Stelle mir 5 kritische Fragen, die ich als Product Owner noch nicht beantwortet habe.

2.) Erstelle 6 User Stories mit je 2 Acceptance Criteria (Format: "Als [X] möcht ich [Y]...")
</font>

# KI-gestützte Lernplattform – Business Analysis

## 1.) Fünf kritische Fragen an den Product Owner

**Frage 1: Datenquellen & Aktualisierungsmechanismus**
Woher bezieht die KI ihre Informationen (Confluence, SharePoint, Git-Repos, Jira, Tickets)? Und vor allem: Wie soll das Problem der veralteten Dokumente gelöst werden – soll die KI nur konsumieren oder auch aktiv Veralterung erkennen und Owner zur Aktualisierung auffordern? Ohne klaren Prozess reproduziert die Plattform sonst nur das bestehende Problem in einem neuen Format.

**Frage 2: Erfolgsmessung & KPIs**
Wie messen wir den Erfolg der Plattform konkret? Reduzierte Time-to-Productivity (von X auf Y Wochen), Mitarbeiterzufriedenheit (eNPS), Anzahl Rückfragen an Senior-Kolleg:innen, Abschlussquote von Lernpfaden? Ohne klare Baseline und Zielwerte können wir später weder ROI nachweisen noch das Produkt iterativ verbessern.

**Frage 3: Rolle der Mentor:innen / Senior-Mitarbeitenden**
Soll die Plattform menschliche Einarbeitung ersetzen, ergänzen oder strukturieren? Was passiert mit dem impliziten Wissen ("tribal knowledge"), das nirgends dokumentiert ist? Die Antwort beeinflusst massgeblich, ob wir z.B. Buddy-Funktionen, Expertensuche oder Wissensextraktions-Interviews einbauen müssen.

**Frage 4: Differenzierung Entwickler:innen vs. Requirement Engineers**
Beide Zielgruppen haben sehr unterschiedliche Lernbedürfnisse (Code/Architektur vs. Stakeholder/Prozesse). Brauchen wir rollenspezifische Lernpfade, oder eine generische Plattform mit Filterfunktionen? Davon hängen Aufwand, Datenmodell und Personalisierungslogik ab.

**Frage 5: Datenschutz, Compliance & KI-Governance**
Welche regulatorischen Vorgaben gelten (DSGVO, interne IT-Security, AI Act)? Dürfen Lernfortschritte gespeichert und ausgewertet werden – und wenn ja, wer hat Zugriff (HR, Vorgesetzte)? Wird ein externes LLM (OpenAI, Anthropic) genutzt oder muss die Lösung on-premise/EU-gehostet sein? Diese Antwort bestimmt Architektur und Anbieterauswahl.

---

## 2.) Sechs User Stories mit Acceptance Criteria

### US-1: Personalisierter Lernpfad
**Als** neu angestellte:r Entwickler:in **möchte ich** beim Onboarding einen auf meine Rolle, mein Team und meine Vorkenntnisse zugeschnittenen Lernpfad erhalten, **damit** ich nicht durch irrelevante Inhalte navigieren muss und schneller produktiv werde.
- AC1: Nach Eingabe von Rolle, Team und Erfahrungslevel generiert das System innerhalb von 30 Sekunden einen strukturierten Lernpfad mit min. 5 Modulen.
- AC2: Der Lernpfad kann jederzeit angepasst werden und der Fortschritt wird persistent gespeichert.

### US-2: Konversationelle Wissensabfrage
**Als** neue:r Mitarbeiter:in **möchte ich** der KI in natürlicher Sprache Fragen zu firmeninternen Themen stellen können, **damit** ich nicht stundenlang Dokumente durchsuchen oder Kolleg:innen stören muss.
- AC1: Die KI antwortet auf Fragen mit Quellenangabe (Link zum Originaldokument) und Aktualitätsdatum der Quelle.
- AC2: Bei Unsicherheit oder fehlenden Informationen gibt die KI dies transparent an und schlägt eine zuständige Person oder Alternativquelle vor.

### US-3: Erkennung veralteter Inhalte
**Als** Plattform-Admin **möchte ich**, dass die KI veraltete oder widersprüchliche Inhalte automatisch erkennt und markiert, **damit** wir die Dokumentenqualität kontinuierlich sicherstellen können.
- AC1: Dokumente, die älter als ein konfigurierbarer Schwellwert sind oder im Widerspruch zu neueren Quellen stehen, werden im Dashboard mit Status "Review nötig" angezeigt.
- AC2: Der hinterlegte Document Owner erhält automatisch eine Benachrichtigung mit konkretem Hinweis auf die zu prüfende Stelle.

### US-4: Gamifizierte Lernerfahrung
**Als** neu angestellte:r Mitarbeiter:in **möchte ich** durch Quizzes, Badges und Fortschrittsanzeigen motiviert werden, **damit** die Einarbeitung abwechslungsreich und nicht ermüdend ist.
- AC1: Nach jedem Lernmodul wird ein Quiz mit min. 3 Fragen angeboten, dessen Bestehen einen Badge im Profil freischaltet.
- AC2: Eine Fortschrittsanzeige visualisiert den Stand des Lernpfads in Prozent und zeigt die nächsten empfohlenen Schritte.

### US-5: Wissensbeitrag durch erfahrene Mitarbeitende
**Als** erfahrene:r Mitarbeiter:in **möchte ich** mein implizites Wissen einfach in die Plattform einspeisen können (z.B. via Sprachaufnahme, Q&A-Form oder Annotation), **damit** Tribal Knowledge nicht verloren geht und für Neueinsteiger:innen verfügbar wird.
- AC1: Beiträge können in mindestens drei Formaten erstellt werden: Texteintrag, Audio-Aufnahme oder Kommentar zu bestehenden Dokumenten.
- AC2: Eingereichte Inhalte durchlaufen einen Review-Workflow durch eine:n fachliche:n Verantwortliche:n, bevor sie für Lernende sichtbar werden.

### US-6: Onboarding-Reporting für HR & Team Leads
**Als** Team Lead **möchte ich** den anonymisierten Lernfortschritt meines neuen Teammitglieds einsehen können, **damit** ich gezielt unterstützen und 1:1-Gespräche vorbereiten kann.
- AC1: Ein Dashboard zeigt aggregierte Metriken (abgeschlossene Module, durchschnittliche Quiz-Ergebnisse, offene Fragen) ohne sensible Inhalte einzelner Antworten.
- AC2: Das neue Teammitglied wird transparent darüber informiert, welche Daten geteilt werden, und kann der Weitergabe widersprechen (Privacy by Design).

---

Möchtest du, dass ich die User Stories priorisiere (MoSCoW), Story Points schätze oder direkt ein erstes Backlog-Refinement-Setup vorbereite?

<font color="cornflowerblue">
Priorisiere die User Stories: US-3 (Erkennung veralteter Inhalte) und US-5 (Wissensbeitrag durch erfahrene Mitarbeitende) sind Must Haves. US-2 (Konversationelle Wissensabfrage) ist Should Have. US-1 (personalisierter Lernpfad) und US-6 (Onboarding-Reporting für HR & Team Leads) sind Could Haves. US-4 (Gamifizierte Lernerfahrung) ist Won't Have this time. Gamifizierte Lernerfahrung ist ok, aber nicht mit Quiz und Fortschrittsanzeige, müsste origineller sein...
</font>

# Priorisiertes Backlog (MoSCoW)

## MUST HAVE
| ID | Story | Begründung |
|---|---|---|
| **US-3** | Erkennung veralteter Inhalte | Adressiert das Kernproblem direkt. Ohne aktuelle Inhalte ist die gesamte Plattform wertlos. |
| **US-5** | Wissensbeitrag durch erfahrene Mitarbeitende | Schliesst die Wissenslücke an der Quelle. Ohne diese Story bleibt das "Veraltete-Dokumente-Problem" ungelöst – die Plattform würde nur konsumieren, nicht regenerieren. |

## SHOULD HAVE
| ID | Story | Begründung |
|---|---|---|
| **US-2** | Konversationelle Wissensabfrage | Hauptnutzen für die Zielgruppe, sollte zum Launch vorhanden sein – ist aber technisch komplex und kann mit einer reduzierten ersten Version (z.B. nur Textsuche mit Quellenangabe) starten. |

## COULD HAVE
| ID | Story | Begründung |
|---|---|---|
| **US-1** | Personalisierter Lernpfad | Wertvoll für UX, aber nicht überlebensnotwendig in MVP. Generischer Pfad pro Rolle als Fallback möglich. |
| **US-6** | Onboarding-Reporting für HR & Team Leads | Sinnvoll für Steuerung, aber Sekundärnutzer:innen. Kann nach Validierung der Hauptfunktionen ergänzt werden. |

## WON'T HAVE (this time)
| ID | Story | Begründung |
|---|---|---|
| ~~US-4~~ | ~~Gamifizierte Lernerfahrung (Quiz + Fortschritt)~~ | Zu generisch, nicht originell genug. Wird ersetzt durch US-4-NEU (siehe unten) – Backlog-Kandidat für spätere Iteration. |

---

## Vorschlag: US-4-NEU (Originellere Gamification-Ideen)

Da Quiz + Fortschrittsbalken nicht differenziert genug sind, hier drei alternative Konzepte. Jedes lässt sich später als eigene User Story formulieren – sag mir, welches Dich anspricht, dann arbeite ich es aus:

### Option A: "Onboarding Quest" – narrative Mission
Neue Mitarbeiter:innen schlüpfen in die Rolle einer:s Detektiv:in / Agent:in, die einen fiktiven internen "Fall" lösen müssen (z.B. "Warum ist das Deployment von Projekt X 2023 gescheitert?"). Dabei lernen sie nebenbei Architektur, Prozesse und Stakeholder kennen. Wissen wird durch Story statt durch Quiz vermittelt.

### Option B: "Real-World Challenges" – echte Mini-Aufgaben
Statt Quizfragen löst die Person echte (aber sandboxed) Aufgaben aus dem Arbeitsalltag: Ein Pull Request reviewen, ein Requirement formulieren, ein Architekturdiagramm interpretieren. Die KI bewertet die Lösung und gibt kontextuelles Feedback. Lernen durch Tun statt durch Multiple Choice.

### Option C: "Knowledge Karma" – soziales Reputationssystem
Mitarbeiter:innen verdienen Punkte nicht durchs Lernen, sondern durchs Beitragen (verknüpft mit US-5): Wer Wissen einspeist, Fragen beantwortet oder veraltete Inhalte meldet, gewinnt Sichtbarkeit. Neue Mitarbeitende sehen, wer Expert:in für welches Thema ist – und werden selbst zu Contributor:innen. Gamification wird zum Treiber für Wissenskultur, nicht für Konsum.

---

Welche Richtung gefällt Dir? Soll ich eine (oder eine Kombination) als ausformulierte User Story mit Acceptance Criteria ergänzen?

<font color="cornflowerblue">
Option C "Knowledge Karma" ist super, kann man zum Must Have machen. Option B ist gut, kann man zum Should Have machen. Option C is Won't Have this time.
</font>

# Kurze Rückfrage zur Priorisierung

Du hast Option C zweimal genannt – einmal als **Must Have** und einmal als **Won't Have**. Das ist vermutlich ein Tippfehler. Ich gehe davon aus, Du meintest:

- **Option C "Knowledge Karma"** → Must Have
- **Option B "Real-World Challenges"** → Should Have
- **Option A "Onboarding Quest"** → Won't Have this time

Stimmt das so? Sobald Du bestätigst, formuliere ich die beiden neuen User Stories (Karma + Real-World Challenges) mit Acceptance Criteria aus und aktualisiere das priorisierte Backlog.

<font color="cornflowerblue">
Stimmt so
</font>

# Aktualisiertes Backlog mit neuen User Stories

## Neue User Stories

### US-7: Knowledge Karma – Reputation für Wissensbeiträge (Must Have)
**Als** Mitarbeiter:in **möchte ich** für meine Beiträge zur Wissensbasis (neue Inhalte, Antworten, Meldungen veralteter Dokumente) sichtbare Anerkennung in Form von "Karma-Punkten" und Expertise-Badges erhalten, **damit** Wissensteilen wertgeschätzt wird und ich als Neue:r schnell die richtigen Ansprechpartner:innen finde.

- **AC1:** Jede:r Mitarbeiter:in hat ein öffentliches Profil mit Karma-Score, Expertise-Themen (automatisch aus Beiträgen abgeleitet) und einer Liste der hilfreichsten Beiträge der letzten 90 Tage.
- **AC2:** Bei der konversationellen Wissensabfrage (US-2) zeigt das System neben den Quellen auch die Top-3-Expert:innen für das jeweilige Thema an, sortiert nach Karma in diesem Bereich.

---

### US-8: Real-World Challenges – Lernen durch echte Aufgaben (Should Have)
**Als** neu angestellte:r Entwickler:in oder Requirement Engineer **möchte ich** statt theoretischer Quizfragen echte, sandboxed Aufgaben aus dem Arbeitsalltag lösen (z.B. Pull Request reviewen, Requirement formulieren, Architekturdiagramm interpretieren), **damit** ich praxisnah lerne und mein Wissen direkt anwenden kann.

- **AC1:** Pro Lernmodul stehen mindestens 2 rollenspezifische Challenges in einer abgeschotteten Sandbox-Umgebung zur Verfügung, die echten internen Szenarien nachempfunden sind.
- **AC2:** Die KI bewertet die Lösung anhand definierter Kriterien und gibt innerhalb von 60 Sekunden kontextuelles Feedback mit Verweis auf Best Practices oder zuständige Expert:innen (Verknüpfung zu US-7).

---

## Konsolidiertes priorisiertes Backlog

### MUST HAVE
| ID | Story | Begründung |
|---|---|---|
| **US-3** | Erkennung veralteter Inhalte | Adressiert das Kernproblem direkt. Ohne aktuelle Inhalte ist die Plattform wertlos. |
| **US-5** | Wissensbeitrag durch erfahrene Mitarbeitende | Schliesst die Wissenslücke an der Quelle – verhindert, dass die Plattform nur konsumiert. |
| **US-7** | Knowledge Karma | Schafft Anreizsystem für US-5 und macht Expertise sichtbar. Treiber für Wissenskultur. |

### SHOULD HAVE
| ID | Story | Begründung |
|---|---|---|
| **US-2** | Konversationelle Wissensabfrage | Hauptnutzen für Lernende; reduzierte Erstversion möglich. |
| **US-8** | Real-World Challenges | Hoher Lerneffekt, aber technisch aufwendig (Sandbox + KI-Bewertung). Kann iterativ wachsen. |

### COULD HAVE
| ID | Story | Begründung |
|---|---|---|
| **US-1** | Personalisierter Lernpfad | Wertvoll für UX, generischer Fallback pro Rolle reicht im MVP. |
| **US-6** | Onboarding-Reporting für HR & Team Leads | Sekundärnutzer:innen, kann später ergänzt werden. |

### WON'T HAVE (this time)
| ID | Story | Begründung |
|---|---|---|
| ~~US-4~~ | ~~Gamifizierte Lernerfahrung (Quiz + Fortschritt)~~ | Zu generisch, ersetzt durch US-7 und US-8. |
| ~~Option A~~ | ~~Onboarding Quest (narrative Mission)~~ | Konzeptionell spannend, aber Aufwand für Story-Design hoch. Backlog-Kandidat für spätere Iteration. |

---

## Beobachtung & Empfehlung

Mit den drei Must Haves (**US-3, US-5, US-7**) entsteht ein in sich geschlossener Wertkreislauf:
- **US-5** bringt neues Wissen rein → **US-7** belohnt es → **US-3** hält es aktuell.

Das ist ein starker MVP-Kern, der das Hauptproblem (veraltete Dokumente, kein Update-Prozess) systemisch adressiert.

Soll ich als nächsten Schritt:
1. **Story Points** für die Must-Haves schätzen (Planning Poker / T-Shirt-Sizing)?
2. Ein **Domain-Modell** skizzieren (Entitäten: User, Beitrag, Karma, Expertise-Tag, Dokument-Status)?
3. Die Must-Have-Stories in **technische Tasks** herunterbrechen?

<font color="cornflowerblue">
Skizziere das Domain-Modell
</font>

# Domain-Modell der Lernplattform

## Übersicht

Das Modell konzentriert sich auf die Must-Haves (US-3, US-5, US-7) und bezieht die Should-Haves (US-2, US-8) als Erweiterungspunkte ein. Could-Haves sind angedeutet, aber nicht ausdetailliert.

---

## Kernentitäten

### 1. User
| Attribut | Typ | Beschreibung |
|---|---|---|
| userId | UUID | Eindeutige ID |
| name, email | String | Identität |
| role | Enum | Developer, RequirementEngineer, TeamLead, Mentor, Admin |
| team | Reference | Zugehöriges Team |
| startDate | Date | Eintrittsdatum (relevant für Onboarding-Status) |
| experienceLevel | Enum | Junior, Mid, Senior |
| totalKarma | Integer | Aggregierter Karma-Score (denormalisiert für Performance) |

### 2. Topic (Expertise-Tag)
| Attribut | Typ | Beschreibung |
|---|---|---|
| topicId | UUID | Eindeutige ID |
| name | String | z.B. "Microservices", "BPMN", "Kubernetes" |
| parentTopicId | UUID? | Hierarchie (z.B. "DevOps" → "Kubernetes") |
| description | Text | Kurzbeschreibung |

### 3. UserExpertise (User ↔ Topic)
| Attribut | Typ | Beschreibung |
|---|---|---|
| userId | FK | Verweis auf User |
| topicId | FK | Verweis auf Topic |
| karmaInTopic | Integer | Themenspezifischer Karma-Score |
| level | Enum | Auto-abgeleitet: Novice / Contributor / Expert |

### 4. KnowledgeItem (Wissensbaustein / Dokument)
| Attribut | Typ | Beschreibung |
|---|---|---|
| itemId | UUID | Eindeutige ID |
| title | String | Titel |
| content | Text/Blob | Inhalt (Text, Audio-Transkript, Link) |
| format | Enum | Text, Audio, Annotation, ExternalLink |
| sourceSystem | Enum | Confluence, SharePoint, Git, Internal |
| ownerId | FK User | Verantwortliche Person |
| createdAt, updatedAt, lastReviewedAt | Timestamp | Lebenszyklus |
| status | Enum | Draft, Active, ReviewNeeded, Outdated, Archived |

### 5. KnowledgeItemTopic (KnowledgeItem ↔ Topic)
M:N-Verknüpfung – ein Dokument kann mehreren Themen zugeordnet sein.

### 6. Contribution
| Attribut | Typ | Beschreibung |
|---|---|---|
| contributionId | UUID | Eindeutige ID |
| userId | FK | Beitragender |
| knowledgeItemId | FK? | Bezug zu Dokument (optional, z.B. bei Antworten) |
| type | Enum | CreateDoc, EditDoc, Annotate, AnswerQuestion, FlagOutdated, ReviewDoc |
| status | Enum | Pending, Approved, Rejected |
| reviewerId | FK User? | Wer hat reviewt (US-5 Review-Workflow) |
| createdAt | Timestamp | |

### 7. KarmaEvent
| Attribut | Typ | Beschreibung |
|---|---|---|
| eventId | UUID | Eindeutige ID |
| userId | FK | Empfänger der Karma |
| contributionId | FK | Auslösender Beitrag |
| topicId | FK | Themenbezug (für UserExpertise.karmaInTopic) |
| points | Integer | +/- (positiv für Beiträge, negativ z.B. bei Rückzug) |
| reason | Enum | NewContent, AcceptedAnswer, OutdatedFlagged, PeerEndorsement |
| timestamp | Timestamp | |

### 8. DocumentReview (für US-3)
| Attribut | Typ | Beschreibung |
|---|---|---|
| reviewId | UUID | |
| knowledgeItemId | FK | Geprüftes Dokument |
| triggeredBy | Enum | AgeThreshold, Contradiction, ManualFlag |
| reviewerId | FK User | Owner oder delegierte Person |
| outcome | Enum | Confirmed, Updated, Archived, Pending |
| reviewedAt | Timestamp | |

### 9. Notification
| Attribut | Typ | Beschreibung |
|---|---|---|
| notificationId | UUID | |
| recipientId | FK User | |
| type | Enum | ReviewNeeded, KarmaEarned, ExpertiseLevelUp, ContributionApproved |
| referenceId | UUID | Bezug (Document, Contribution, etc.) |
| readAt | Timestamp? | |

### 10. Question & Answer (für US-2)
| Attribut | Typ | Beschreibung |
|---|---|---|
| questionId | UUID | |
| askerUserId | FK | Fragesteller |
| text | Text | Originalfrage |
| aiResponse | Text | KI-Antwort |
| sourceItems | M:N → KnowledgeItem | Belegquellen |
| suggestedExperts | M:N → User | Top-Expert:innen via UserExpertise.karmaInTopic |
| confidence | Float | Sicherheit der KI |

### 11. Challenge & ChallengeAttempt (für US-8)
**Challenge:** challengeId, title, description, role (Zielrolle), topicId, sandboxConfig
**ChallengeAttempt:** attemptId, userId, challengeId, submission, aiFeedback, score, completedAt

---

## Beziehungsdiagramm (ER-Notation)

```
                    ┌─────────────┐
                    │    User     │◄──────────────────────┐
                    └──────┬──────┘                       │
                           │ 1                            │
            ┌──────────────┼──────────────┐               │
            │ N            │ N            │ N             │
    ┌───────▼──────┐ ┌─────▼────────┐ ┌───▼──────────┐    │
    │ Contribution │ │ KarmaEvent   │ │UserExpertise │    │
    └───────┬──────┘ └─────┬────────┘ └───┬──────────┘    │
            │ N            │ N            │ N             │
            │              │              │               │
            │              ▼              ▼               │
            │         ┌────────┐    ┌────────┐            │
            │         │ Topic  │◄───┤ Topic  │            │
            │         └────┬───┘    └────────┘            │
            │ N            │ N                            │
            ▼              ▼                              │
    ┌──────────────────────────┐    N      ┌──────────────┴───┐
    │     KnowledgeItem        ├──────────►│ DocumentReview   │
    │  (status, lastReview)    │           └──────────────────┘
    └──────────┬───────────────┘
               │ N
               │
    ┌──────────▼───────────────┐
    │   Question (AI Q&A)      │
    │  - sourceItems           │
    │  - suggestedExperts ────────► User (via Expertise)
    └──────────────────────────┘
```

---

## Wichtige Geschäftsregeln (Invarianten)

1. **Karma kann nur durch genehmigte Contributions entstehen.**
   `KarmaEvent` darf nur erzeugt werden, wenn die zugehörige `Contribution.status = Approved`.

2. **Expertise wird automatisch abgeleitet, nicht manuell vergeben.**
   `UserExpertise.level` ergibt sich aus `karmaInTopic` (z.B. >100 = Expert). Kein Self-Assessment.

3. **Jedes KnowledgeItem hat genau einen Owner.**
   Wenn der Owner das Unternehmen verlässt, muss vor Deaktivierung des Accounts ein neuer Owner zugewiesen werden (sonst → Status `ReviewNeeded`).

4. **Review-Trigger sind systemgesteuert.**
   Status `ReviewNeeded` wird automatisch gesetzt durch:
   - Alter > Schwellwert (konfigurierbar pro Topic)
   - Widerspruchserkennung der KI gegenüber neueren Quellen
   - Manuelles Flagging via `Contribution.type = FlagOutdated`

5. **Beiträge durchlaufen Review vor Veröffentlichung.**
   Neue/geänderte `KnowledgeItems` aus US-5 sind erst nach `Contribution.status = Approved` für Lernende sichtbar.

6. **Karma-Quelle ist transparent.**
   Jeder Punkt ist über `KarmaEvent` rückverfolgbar – kein "magischer" Score.

---

## Mapping zu Must-Have User Stories

| Story | Zentrale Entitäten |
|---|---|
| **US-3** Erkennung veralteter Inhalte | `KnowledgeItem.status`, `DocumentReview`, `Notification` |
| **US-5** Wissensbeitrag erfahrener Mitarbeitender | `Contribution`, `KnowledgeItem`, Review-Workflow über `Contribution.reviewerId` |
| **US-7** Knowledge Karma | `KarmaEvent`, `UserExpertise`, `Topic`, abgeleitete Expert:innen-Empfehlungen |

---

## Offene Modellierungsfragen

1. **Versionierung:** Sollen `KnowledgeItem`-Änderungen historisiert werden (Audit-Trail)? Empfehlung: ja, separate `KnowledgeItemVersion`-Tabelle.
2. **Karma-Decay:** Verfällt Karma über Zeit (Anreiz zu kontinuierlichem Beitragen) oder bleibt es kumulativ?
3. **Negative Karma:** Können Beiträge mit "wenig hilfreich" bewertet werden (Risiko: demotivierend)?
4. **Anonymität:** Können Fragen anonym gestellt werden (Schutz vor Hemmschwelle bei "dummen" Fragen)?
5. **Topic-Pflege:** Sind Topics fest vorgegeben (Taxonomie) oder können sie organisch wachsen (Folksonomy)?

---

Soll ich als Nächstes:
1. Die **offenen Modellierungsfragen** mit Dir durchgehen und Empfehlungen geben?
2. Ein **Sequenzdiagramm** für einen zentralen Flow zeichnen (z.B. "Beitrag erstellen → Review → Karma vergeben")?
3. Die Must-Have-Stories in **technische Tasks** herunterbrechen?

<font color="cornflowerblue">
Die offenen Modellierungsfragen durchgehen!
</font>

# Offene Modellierungsfragen – Diskussion & Empfehlungen

Für jede Frage findest Du: Optionen, Empfehlung mit Begründung und Auswirkungen aufs Modell.

---

## Frage 1: Versionierung von KnowledgeItems

**Worum geht's?**
Sollen Änderungen an Dokumenten historisiert werden, sodass nachvollziehbar ist, wer wann was geändert hat – inklusive der Möglichkeit, alte Stände einzusehen?

**Optionen:**
| Option | Beschreibung | Aufwand |
|---|---|---|
| A | Keine Versionierung – nur aktueller Stand | Niedrig |
| B | Einfache Audit-Logs (wer, wann, was) | Mittel |
| C | Vollständige Versionierung mit Diff & Rollback | Hoch |

**Empfehlung: Option B im MVP, Option C als Erweiterung**

**Begründung:**
- Compliance & Vertrauen: Lernende müssen erkennen können, *wann* ein Inhalt geändert wurde – wichtig für die Glaubwürdigkeit nach US-3.
- Reviewer:innen brauchen Kontext: "Was hat sich seit dem letzten Review geändert?" ist eine zentrale Frage.
- Vollständige Versionierung mit Diff/Rollback ist mächtig, aber aufwendig. Sie ist erst sinnvoll, wenn das System produktiv genutzt wird und Konflikte tatsächlich auftreten.

**Auswirkung auf Modell:**
Neue Entität `KnowledgeItemAudit`:
```
auditId, knowledgeItemId, changedBy (User), changedAt,
changeType (Created/Updated/StatusChanged), changeSummary
```

---

## Frage 2: Karma-Decay (Verfall über Zeit)

**Worum geht's?**
Soll Karma nach einer Zeit verfallen (z.B. Beiträge älter als 12 Monate zählen weniger), um zu kontinuierlichem Beitragen zu motivieren – oder bleibt Karma dauerhaft kumulativ?

**Optionen:**
| Option | Beschreibung |
|---|---|
| A | Kumulativ – einmal verdient, immer behalten |
| B | Decay – Karma reduziert sich z.B. um 50% pro Jahr |
| C | Hybrid – "All-Time Karma" + "Active Karma" (letzte 12 Monate) |

**Empfehlung: Option C (Hybrid)**

**Begründung:**
- Pures Decay (B) demotiviert langjährige Mitarbeitende und erscheint "unfair" – wer früh viel beigetragen hat, verliert Anerkennung.
- Pure Kumulation (A) führt dazu, dass langjährige Mitarbeitende dominieren, auch wenn sie nichts mehr beitragen. Neue Expert:innen werden unsichtbar.
- Hybrid (C) löst beides: All-Time Karma würdigt Lebenswerk, Active Karma spiegelt aktuelle Relevanz – wichtig für die Expert:innen-Empfehlung in US-2.

**Auswirkung auf Modell:**
`UserExpertise` erhält zwei Felder:
```
karmaInTopicAllTime: Integer
karmaInTopicActive:  Integer  (rolling 12 Monate, nightly recalculated)
```
Die Expert:innen-Empfehlung in US-2 nutzt `karmaInTopicActive`.

---

## Frage 3: Negative Bewertungen / Downvotes

**Worum geht's?**
Können Beiträge als "wenig hilfreich" markiert werden – mit dem Risiko, dass Mitarbeitende sich nicht mehr trauen beizutragen?

**Optionen:**
| Option | Beschreibung |
|---|---|
| A | Keine negativen Signale – nur "hilfreich"-Endorsements |
| B | Downvotes mit Karma-Abzug |
| C | "Veraltet melden" als einziges negatives Signal (kein direkter Karma-Abzug) |

**Empfehlung: Option C**

**Begründung:**
- Downvotes (B) sind in einem Unternehmenskontext kulturell heikel – Stack-Overflow-Mechaniken funktionieren dort, weil die Community anonym und gross ist. Im Unternehmen kennt man sich, und Downvotes können als persönlicher Angriff wirken.
- Pures Endorsement (A) ist zu zahnlos – schlechte Inhalte bleiben unkommentiert stehen.
- Option C nutzt die bestehende `Contribution.type = FlagOutdated`-Mechanik: Inhalte werden nicht "schlecht" bewertet, sondern als "veraltet" markiert. Das ist konstruktiv und passt zum Kernziel der Plattform (US-3).
- Wichtig: Wer flaggt, bekommt selbst Karma (positive Verstärkung), die Original-Autor:innen verlieren keine Karma.

**Auswirkung auf Modell:**
Keine Änderung – `Contribution.type = FlagOutdated` und `KarmaEvent.reason = OutdatedFlagged` sind bereits modelliert. Wichtig: explizit dokumentieren, dass beim Flaggen *kein* negativer KarmaEvent für den/die ursprüngliche:n Autor:in entsteht.

---

## Frage 4: Anonyme Fragen

**Worum geht's?**
Können neue Mitarbeiter:innen Fragen anonym stellen, um die Hemmschwelle für "vermeintlich dumme" Fragen zu senken?

**Optionen:**
| Option | Beschreibung |
|---|---|
| A | Immer mit Klarnamen |
| B | Immer anonym gegenüber anderen Usern, intern verknüpft |
| C | Wählbar pro Frage durch Fragesteller:in |

**Empfehlung: Option C, mit Default "anonym" für die ersten 90 Tage**

**Begründung:**
- A ist häufige Realität in Unternehmens-Wikis und ein bekannter Hemmschuh – "Will ich, dass meine erste Frage als Junior für immer in der Suche auftaucht?"
- Pure Anonymität (B) verhindert direkte Rückfragen und persönliche Beziehungen.
- Option C gibt Kontrolle. Default-Anonymität in der Onboarding-Phase senkt aktiv die Hemmschwelle, danach wechselt der Default zu Klarnamen (Beziehungsaufbau).
- Wichtig für Vertrauen: Auch in der "anonymen" Variante muss intern (z.B. für Moderation, Missbrauchsprävention) eine Verknüpfung zur Person bestehen.

**Auswirkung auf Modell:**
`Question` erhält Felder:
```
askerUserId:    FK User      (intern immer gespeichert)
displayMode:    Enum (Public, Anonymous)
```
Beim Anzeigen wird `askerUserId` nur an Admins/Moderator:innen ausgeliefert, wenn `displayMode = Anonymous`.

---

## Frage 5: Topic-Pflege – Taxonomie vs. Folksonomy

**Worum geht's?**
Sind die Themen (Topics) fest vorgegeben (kontrollierte Taxonomie) oder können sie von Nutzer:innen frei vergeben werden und organisch wachsen (Folksonomy à la Stack Overflow Tags)?

**Optionen:**
| Option | Beschreibung |
|---|---|
| A | Feste Taxonomie – nur Admins legen Topics an |
| B | Reine Folksonomy – jede:r kann neue Tags vergeben |
| C | Hybrid – kontrollierte Top-Level-Topics, freie Tags darunter |

**Empfehlung: Option C**

**Begründung:**
- Reine Taxonomie (A) ist sauber, aber wartungsintensiv und langsam. Neue Themen (z.B. ein neues Framework) brauchen Admin-Approval, bevor sie sichtbar werden.
- Reine Folksonomy (B) führt zu Wildwuchs: "Kubernetes", "k8s", "K8S" als drei separate Tags – das verfälscht Karma-Berechnungen und Expert:innen-Empfehlungen.
- Hybrid (C): Top-Level-Topics ("Backend", "Frontend", "Requirements", "DevOps") sind kuratiert. Darunter dürfen User freie Tags vergeben, die periodisch (z.B. quartalsweise) durch Admins konsolidiert werden ("k8s" → "kubernetes").
- Wichtig für US-7: Karma muss auf konsolidierten Tags aggregiert werden, sonst ist die Expert:innen-Empfehlung verzerrt.

**Auswirkung auf Modell:**
`Topic` erhält ein Feld:
```
type: Enum (Curated, UserGenerated)
canonicalTopicId: UUID?  (für Synonym-Mapping nach Konsolidierung)
```
Hilfsentität: `TopicMergeLog` (für Audit beim Zusammenführen).

---

## Zusammenfassung der Empfehlungen

| # | Frage | Empfehlung |
|---|---|---|
| 1 | Versionierung | Audit-Logs im MVP, volle Versionierung später |
| 2 | Karma-Decay | Hybrid (All-Time + Active) |
| 3 | Downvotes | Keine – nur "Veraltet melden" als negatives Signal |
| 4 | Anonyme Fragen | Wählbar, anonym als Default in den ersten 90 Tagen |
| 5 | Topic-Pflege | Hybrid (kuratierte Top-Level + freie Tags mit periodischer Konsolidierung) |

---

## Querbezüge & implizite Designentscheidungen

Diese fünf Entscheidungen ergeben zusammen ein **psychologisch sicheres Beitragsklima**:
- Keine Downvotes (Frage 3) + anonyme Fragen (Frage 4) = niedrige Hemmschwelle
- Active Karma (Frage 2) + Karma fürs Flaggen (Frage 3) = kontinuierliche Aktivität wird belohnt
- Audit-Trail (Frage 1) + Topic-Konsolidierung (Frage 5) = Datenqualität bleibt erhalten

Das ist konsistent mit dem MVP-Kern (Kreislauf US-3 + US-5 + US-7).

---

Möchtest Du, dass ich:
1. Das **Domain-Modell entsprechend aktualisiere** (mit den neuen Feldern aus den Empfehlungen)?
2. Diese Designentscheidungen als **Architecture Decision Records (ADRs)** dokumentiere?
3. Mit dem **Sequenzdiagramm "Beitrag erstellen → Review → Karma vergeben"** weitermache?

<font color="cornflowerblue">
Das Domain-Modell entsprechend aktualisieren!
</font>

# Aktualisiertes Domain-Modell

Änderungen aus den Empfehlungen sind mit 🆕 markiert.

---

## Kernentitäten (aktualisiert)

### 1. User
| Attribut | Typ | Beschreibung |
|---|---|---|
| userId | UUID | Eindeutige ID |
| name, email | String | Identität |
| role | Enum | Developer, RequirementEngineer, TeamLead, Mentor, Admin |
| team | Reference | Zugehöriges Team |
| startDate | Date | Eintrittsdatum (relevant für Onboarding-Status & Anonymitäts-Default) |
| experienceLevel | Enum | Junior, Mid, Senior |
| totalKarmaAllTime | Integer | 🆕 Lebenswerk (kumulativ) |
| totalKarmaActive | Integer | 🆕 Aktive Karma (rolling 12 Monate) |

### 2. Topic
| Attribut | Typ | Beschreibung |
|---|---|---|
| topicId | UUID | Eindeutige ID |
| name | String | z.B. "Microservices", "BPMN", "Kubernetes" |
| parentTopicId | UUID? | Hierarchie |
| description | Text | Kurzbeschreibung |
| type | Enum | 🆕 Curated, UserGenerated |
| canonicalTopicId | UUID? | 🆕 Verweis auf konsolidiertes Topic (Synonym-Mapping) |
| createdBy | FK User | 🆕 Wer hat das Topic angelegt |
| createdAt | Timestamp | 🆕 |

### 3. UserExpertise (User ↔ Topic)
| Attribut | Typ | Beschreibung |
|---|---|---|
| userId | FK | Verweis auf User |
| topicId | FK | Verweis auf Topic (nur kanonische Topics zählen) |
| karmaInTopicAllTime | Integer | 🆕 Kumulativ |
| karmaInTopicActive | Integer | 🆕 Rolling 12 Monate (nightly recalculated) |
| level | Enum | Auto-abgeleitet aus `karmaInTopicActive`: Novice / Contributor / Expert |
| lastRecalculatedAt | Timestamp | 🆕 Zeitstempel der letzten Active-Berechnung |

### 4. KnowledgeItem
| Attribut | Typ | Beschreibung |
|---|---|---|
| itemId | UUID | Eindeutige ID |
| title | String | Titel |
| content | Text/Blob | Inhalt |
| format | Enum | Text, Audio, Annotation, ExternalLink |
| sourceSystem | Enum | Confluence, SharePoint, Git, Internal |
| ownerId | FK User | Verantwortliche Person |
| createdAt, updatedAt, lastReviewedAt | Timestamp | Lebenszyklus |
| status | Enum | Draft, Active, ReviewNeeded, Outdated, Archived |
| currentVersion | Integer | 🆕 Aktuelle Versionsnummer (zählt mit Audit-Einträgen) |

### 5. KnowledgeItemTopic
M:N – ein Dokument kann mehreren (kanonischen) Topics zugeordnet sein.

### 6. 🆕 KnowledgeItemAudit (NEU)
| Attribut | Typ | Beschreibung |
|---|---|---|
| auditId | UUID | Eindeutige ID |
| knowledgeItemId | FK | Bezug zum Dokument |
| versionNumber | Integer | Inkrementell |
| changedBy | FK User | Wer hat geändert |
| changedAt | Timestamp | Wann |
| changeType | Enum | Created, ContentUpdated, StatusChanged, OwnerChanged, TopicsChanged |
| changeSummary | Text | Kurzbeschreibung der Änderung |

> **Hinweis:** MVP-Variante ohne vollständigen Diff/Rollback. Erweiterung auf vollwertige Versionierung möglich, ohne Schema zu brechen.

### 7. Contribution
| Attribut | Typ | Beschreibung |
|---|---|---|
| contributionId | UUID | Eindeutige ID |
| userId | FK | Beitragender |
| knowledgeItemId | FK? | Bezug zu Dokument (optional) |
| type | Enum | CreateDoc, EditDoc, Annotate, AnswerQuestion, FlagOutdated, ReviewDoc |
| status | Enum | Pending, Approved, Rejected |
| reviewerId | FK User? | Reviewer |
| createdAt | Timestamp | |

### 8. KarmaEvent
| Attribut | Typ | Beschreibung |
|---|---|---|
| eventId | UUID | Eindeutige ID |
| userId | FK | Empfänger der Karma |
| contributionId | FK | Auslösender Beitrag |
| topicId | FK | Themenbezug (immer kanonisch) |
| points | Integer | Nur positive Werte (siehe Regel 7) |
| reason | Enum | NewContent, AcceptedAnswer, OutdatedFlagged, PeerEndorsement |
| timestamp | Timestamp | Relevant für Active-Karma-Berechnung |

### 9. DocumentReview
| Attribut | Typ | Beschreibung |
|---|---|---|
| reviewId | UUID | |
| knowledgeItemId | FK | Geprüftes Dokument |
| triggeredBy | Enum | AgeThreshold, Contradiction, ManualFlag |
| reviewerId | FK User | Owner oder delegierte Person |
| outcome | Enum | Confirmed, Updated, Archived, Pending |
| reviewedAt | Timestamp | |

### 10. Notification
| Attribut | Typ | Beschreibung |
|---|---|---|
| notificationId | UUID | |
| recipientId | FK User | |
| type | Enum | ReviewNeeded, KarmaEarned, ExpertiseLevelUp, ContributionApproved |
| referenceId | UUID | Bezug |
| readAt | Timestamp? | |

### 11. Question
| Attribut | Typ | Beschreibung |
|---|---|---|
| questionId | UUID | |
| askerUserId | FK | 🔒 Intern immer gespeichert (Moderation, Audit) |
| displayMode | Enum | 🆕 Public, Anonymous |
| text | Text | Originalfrage |
| aiResponse | Text | KI-Antwort |
| sourceItems | M:N → KnowledgeItem | Belegquellen |
| suggestedExperts | M:N → User | Top-Expert:innen via `karmaInTopicActive` |
| confidence | Float | Sicherheit der KI |
| createdAt | Timestamp | |

> **Default-Regel:** Wenn `User.startDate` < 90 Tage zurückliegt → `displayMode = Anonymous` als Default. User kann jederzeit umstellen.

### 12. 🆕 TopicMergeLog (NEU)
| Attribut | Typ | Beschreibung |
|---|---|---|
| mergeId | UUID | |
| sourceTopicId | FK Topic | Topic, das zusammengeführt wurde |
| canonicalTopicId | FK Topic | Ziel-Topic |
| mergedBy | FK User | Admin, der die Zusammenführung durchgeführt hat |
| mergedAt | Timestamp | |
| reason | Text | Begründung (z.B. "Synonym k8s → kubernetes") |

### 13. Challenge / ChallengeAttempt (US-8, unverändert)

---

## Aktualisiertes Beziehungsdiagramm

```
                            ┌─────────────┐
                            │    User     │◄──────────────────────┐
                            │ (Karma:     │                       │
                            │  AllTime,   │                       │
                            │  Active)    │                       │
                            └──────┬──────┘                       │
                                   │ 1                            │
              ┌────────────────────┼────────────────────┐         │
              │ N                  │ N                  │ N       │
      ┌───────▼──────┐     ┌───────▼──────┐     ┌───────▼──────┐  │
      │ Contribution │     │ KarmaEvent   │     │UserExpertise │  │
      │              │     │ (timestamped │     │ (AllTime +   │  │
      │              │     │  for Active) │     │  Active)     │  │
      └───────┬──────┘     └───────┬──────┘     └───────┬──────┘  │
              │ 1                  │ N                  │ N       │
              │                    │                    │         │
              │                    ▼                    ▼         │
              │              ┌──────────────────────────────┐     │
              │              │           Topic              │     │
              │              │ (Curated/UserGenerated,      │     │
              │              │  canonicalTopicId)           │     │
              │              └──────────────┬───────────────┘     │
              │ N                           │ N                   │
              ▼                             │                     │
      ┌──────────────────────────┐    N     │     ┌───────────────▼──┐
      │     KnowledgeItem        ├──────────┘     │ DocumentReview   │
      │ (status, currentVersion) │                └──────────────────┘
      └──┬───────────────────┬───┘
         │ 1                 │ 1
         │                   │
         ▼ N                 ▼ N
   ┌──────────────┐    ┌─────────────────────┐
   │KnowledgeItem │    │   Question (AI Q&A) │
   │   Audit      │    │ - displayMode       │
   │ (NEU)        │    │ - askerUserId 🔒    │
   │              │    │ - sourceItems       │
   │              │    │ - suggestedExperts ─────► User (via Active Karma)
   └──────────────┘    └─────────────────────┘

   ┌──────────────────────────┐
   │   TopicMergeLog (NEU)    │──── Topic (source & canonical)
   └──────────────────────────┘
```

---

## Aktualisierte Geschäftsregeln (Invarianten)

1. **Karma kann nur durch genehmigte Contributions entstehen.**
   `KarmaEvent` darf nur bei `Contribution.status = Approved` erzeugt werden.

2. **Expertise wird automatisch abgeleitet, nicht manuell vergeben.**
   `UserExpertise.level` ergibt sich aus `karmaInTopicActive`.

3. **Jedes KnowledgeItem hat genau einen Owner.**
   Vor Account-Deaktivierung muss ein neuer Owner zugewiesen werden.

4. **Review-Trigger sind systemgesteuert.**
   Status `ReviewNeeded` wird automatisch gesetzt durch Alter, Widerspruchserkennung oder manuelles Flagging.

5. **Beiträge durchlaufen Review vor Veröffentlichung.**
   Neue/geänderte `KnowledgeItems` aus US-5 sind erst nach Approval sichtbar.

6. **Karma-Quelle ist transparent.**
   Jeder Punkt ist über `KarmaEvent` rückverfolgbar.

7. 🆕 **Karma ist nicht-negativ.**
   `KarmaEvent.points > 0`. Flaggen veralteter Inhalte führt nicht zu Karma-Abzug für Original-Autor:in, nur zu Karma-Gewinn für Flaggende.

8. 🆕 **Karma-Berechnung erfolgt zweistufig.**
   - `karmaInTopicAllTime`: Summe aller `KarmaEvent.points` für (User, Topic)
   - `karmaInTopicActive`: Summe aller `KarmaEvent.points` für (User, Topic) mit `timestamp >= now() - 12 Monate`
   - Nightly Job aktualisiert Active-Werte und `UserExpertise.level`.

9. 🆕 **Karma wird ausschliesslich auf kanonischen Topics aggregiert.**
   Bei `KnowledgeItemTopic` werden UserGenerated Tags erlaubt, aber `KarmaEvent.topicId` muss auf ein Topic mit `canonicalTopicId = NULL` zeigen (oder das aufgelöste kanonische Topic). Topic-Merges via `TopicMergeLog` re-aggregieren historische Karma-Events.

10. 🆕 **Jede Änderung an KnowledgeItem erzeugt einen Audit-Eintrag.**
    `KnowledgeItemAudit` wird bei jeder Mutation geschrieben, `currentVersion` wird inkrementiert.

11. 🆕 **Anonymität schützt nach aussen, nicht nach innen.**
    `Question.askerUserId` ist immer gesetzt. Bei `displayMode = Anonymous` wird `askerUserId` nur an Rollen `Admin` und `Mentor` (Moderation) ausgeliefert. Für alle anderen erscheint die Frage als "anonym".

12. 🆕 **Anonymitäts-Default ist zeitgesteuert.**
    Bei neuen Fragen: wenn `User.startDate > now() - 90 Tage`, dann Default `displayMode = Anonymous`. Sonst Default `Public`. User kann immer umstellen.

---

## Zusammenfassung der Änderungen

| Bereich | Änderung |
|---|---|
| **User** | Karma in zwei Dimensionen (AllTime + Active) |
| **UserExpertise** | Karma in zwei Dimensionen + Recalculation-Timestamp |
| **Topic** | Type (Curated/UserGenerated) + canonicalTopicId für Synonym-Mapping |
| **KnowledgeItem** | currentVersion-Feld |
| **KnowledgeItemAudit** | NEUE Entität für Audit-Trail |
| **Question** | displayMode (Public/Anonymous) + Default-Regel |
| **TopicMergeLog** | NEUE Entität für Topic-Konsolidierung |
| **Geschäftsregeln** | 6 neue Invarianten ergänzt (Regeln 7–12) |

---

## Was noch offen ist (für später)

- **Schwellwerte konkretisieren:** Wann genau wechselt jemand von Contributor zu Expert? Wie viele Karma pro Beitragsart? → eigener Workshop "Karma-Ökonomie".
- **Permissions-Modell:** Wer darf Topics mergen, wer darf Reviews delegieren? → eigene Story für Admin-Funktionen.
- **Internationalisierung:** Wenn Inhalte mehrsprachig sind (DE/EN), braucht `KnowledgeItem` ggf. eine `language`-Dimension.

---

Möchtest Du als Nächstes:
1. Die **Karma-Ökonomie konkretisieren** (Punktewerte, Schwellwerte, Level-Definitionen)?
2. Das **Sequenzdiagramm "Beitrag erstellen → Review → Karma vergeben"** zeichnen?
3. Die Must-Have-Stories in **technische Tasks** herunterbrechen?

<font color="cornflowerblue">
Must-Have-Stories in technische Tasks herunterbrechen!
</font>

# Technisches Task-Breakdown der Must-Have Stories

## Struktur

Tasks gliedern sich in:
- **F – Foundation** (Cross-cutting, von allen Stories benötigt)
- **US-3, US-5, US-7** (Story-spezifisch)
- T-Shirt-Sizing: **XS** (≤0.5d), **S** (1–2d), **M** (3–5d), **L** (1–2w), **XL** (>2w → splitten!)

---

## Foundation Tasks (vorab oder parallel)

| ID | Task | Größe | Beschreibung |
|---|---|---|---|
| F-1 | DB-Schema initialisieren | M | Tabellen aus Domain-Modell anlegen (User, Topic, KnowledgeItem, Contribution, KarmaEvent, etc.) inkl. Migrations-Setup (z.B. Flyway/Liquibase) |
| F-2 | Authentifizierung & SSO-Anbindung | M | Anbindung an internes IdP (z.B. Azure AD/Entra), Rollen-Mapping (Developer, RE, Admin, Mentor, TeamLead) |
| F-3 | API-Gateway & Basis-Backend | M | REST/GraphQL-Setup, Logging, Error-Handling, Health-Checks |
| F-4 | Frontend-Grundgerüst | M | App-Shell, Routing, Auth-Integration, Design-System-Basis |
| F-5 | CI/CD-Pipeline | M | Build, Test, Deploy auf Dev/Staging/Prod, automatisierte Migrations |
| F-6 | Source-System-Konnektoren (Confluence, SharePoint, Git) | L | Lese-Zugriff, Sync-Mechanismus, Mapping zu `KnowledgeItem` |
| F-7 | LLM-Integration (Provider-Abstraktion) | M | Wrapper für externes/internes LLM, Prompt-Templates, Token-Tracking, Fallback |
| F-8 | Notification-Service | S | E-Mail / In-App, Queue-basiert, Templating |
| F-9 | Audit- & Logging-Infrastruktur | S | Strukturiertes Logging, Tracing (OpenTelemetry), DSGVO-konformes Storage |
| F-10 | Monitoring & Alerting | S | Dashboards (Karma-Vergabe, Review-Queue-Länge, KI-Latenz), Alerts auf Anomalien |

---

## US-3: Erkennung veralteter Inhalte

**Story-Ziel:** System erkennt veraltete/widersprüchliche Inhalte automatisch und benachrichtigt Owner.

| ID | Task | Größe | Abhängigkeit | Beschreibung |
|---|---|---|---|---|
| US3-T1 | Schwellwert-Konfiguration (Backend) | S | F-1 | Konfigurierbare Schwellwerte pro Topic (z.B. "Kubernetes-Docs nach 6 Monaten reviewen") inkl. Admin-API |
| US3-T2 | Age-Trigger-Job | S | F-1, US3-T1 | Nightly Job: scannt `KnowledgeItem.lastReviewedAt`, setzt Status `ReviewNeeded` bei Überschreitung |
| US3-T3 | Widerspruchserkennung via LLM | L | F-7 | Embedding-basierte Ähnlichkeitssuche zwischen Dokumenten + LLM-Prompt zur Konsistenzprüfung. Output: Confidence-Score + Begründung |
| US3-T4 | Manuelles Flaggen (API + UI) | S | F-3, F-4 | Button "Inhalt veraltet melden" → erzeugt `Contribution(type=FlagOutdated)` und triggert `DocumentReview` |
| US3-T5 | Review-Workflow Backend | M | F-1, F-8 | State-Machine für `DocumentReview` (Triggered → Pending → Confirmed/Updated/Archived), Owner-Benachrichtigung |
| US3-T6 | Review-Dashboard (Frontend) | M | F-4, US3-T5 | Liste aller `KnowledgeItem` mit Status `ReviewNeeded`, Filter nach Topic/Owner/Trigger-Typ, Bulk-Aktionen |
| US3-T7 | Owner-Benachrichtigungen | S | F-8, US3-T5 | Notification mit konkreter Stelle (Diff-Hinweis bei Widerspruch, Alter bei Age-Trigger) |
| US3-T8 | Audit-Trail-Integration | S | F-1 | Jede Status-Änderung eines `KnowledgeItem` schreibt `KnowledgeItemAudit` |
| US3-T9 | E2E-Tests US-3 | S | alle US3-T* | Szenarien: Age-Trigger, manuelles Flaggen, Owner-Bestätigung |

**Empfohlene Sequenz:** T1 → T2 → T4 → T5 → T6 → T7 → T8 → (T3 später, da KI-Komponente komplex)

---

## US-5: Wissensbeitrag erfahrener Mitarbeitender

**Story-Ziel:** Erfahrene Mitarbeitende speisen Wissen in mehreren Formaten ein, durchlaufen Review-Workflow.

| ID | Task | Größe | Abhängigkeit | Beschreibung |
|---|---|---|---|---|
| US5-T1 | Beitrags-API (Text) | S | F-1, F-3 | POST/PUT für `KnowledgeItem` mit Format `Text`, inkl. Topic-Zuordnung |
| US5-T2 | Beitrags-UI (Text-Editor) | M | F-4, US5-T1 | Markdown/WYSIWYG-Editor, Topic-Picker (Curated + Free-Tag), Preview |
| US5-T3 | Audio-Upload + Transkription | M | F-7, US5-T1 | Upload-Endpoint, asynchrone Transkription via Speech-to-Text-Service, Speicherung als `format=Audio` mit Transkript |
| US5-T4 | Annotation auf bestehenden Dokumenten | M | US5-T1 | UI: Textstelle markieren → Kommentar/Ergänzung anhängen. Backend: `KnowledgeItem` mit `format=Annotation` und Verweis auf Original |
| US5-T5 | Review-Workflow Backend | M | F-1, F-8 | `Contribution.status` (Pending → Approved/Rejected), Reviewer-Zuweisung (Owner des Topics oder Default-Mentor) |
| US5-T6 | Review-UI für Reviewer:innen | M | F-4, US5-T5 | Inbox mit ausstehenden Beiträgen, Approve/Reject mit Kommentar, Diff-Anzeige bei Edits |
| US5-T7 | Sichtbarkeitssteuerung | S | US5-T5 | Beiträge mit Status `Pending` nur für Autor:in + Reviewer:in sichtbar; nach `Approved` für alle |
| US5-T8 | Topic-Tagging (Hybrid-Modell) | S | F-1 | Curated Topics aus DB, freie Tags eingebbar; Auto-Suggest aus existierenden UserGenerated-Tags |
| US5-T9 | Topic-Konsolidierung (Admin-UI) | M | US5-T8 | Admin-View: Liste aller UserGenerated-Tags, Merge-Funktion (`TopicMergeLog`), automatisches Re-Mapping aller Karma-Events |
| US5-T10 | Karma-Vergabe-Trigger | XS | US7-T1 | Bei `Contribution.status → Approved`: triggert KarmaEvent (siehe US7-T2) |
| US5-T11 | E2E-Tests US-5 | S | alle US5-T* | Szenarien: Text-Beitrag → Review → Approve → Sichtbar; Audio-Upload mit Transkript; Annotation |

**Empfohlene Sequenz:** T1 → T2 → T5 → T6 → T7 → T8 → T10 → T11 (Audio T3 + Annotation T4 + Konsolidierung T9 als zweite Welle)

---

## US-7: Knowledge Karma

**Story-Ziel:** Karma-System belohnt Beiträge, leitet Expertise ab, macht Expert:innen sichtbar.

| ID | Task | Größe | Abhängigkeit | Beschreibung |
|---|---|---|---|---|
| US7-T1 | Karma-Regelwerk-Konfiguration | S | F-1 | Konfigurierbare Punktewerte pro `KarmaEvent.reason` (z.B. NewContent=10, AcceptedAnswer=5, OutdatedFlagged=3, PeerEndorsement=1) |
| US7-T2 | KarmaEvent-Service | S | F-1, US7-T1 | Erzeugt `KarmaEvent`, aktualisiert `User.totalKarmaAllTime` und `UserExpertise.karmaInTopicAllTime` transaktional |
| US7-T3 | Active-Karma-Recalculation-Job | M | US7-T2 | Nightly Job: berechnet `karmaInTopicActive` (rolling 12 Monate), aktualisiert `UserExpertise.level` |
| US7-T4 | Profil-API & UI | M | F-3, F-4, US7-T2 | User-Profil zeigt Karma-Score, Top-Expertise-Topics, letzte Beiträge (90 Tage), Level-Badges |
| US7-T5 | Peer-Endorsement-Mechanik | S | US7-T2 | Button "War hilfreich" auf Beiträgen → erzeugt `Contribution(type=PeerEndorsement)` + KarmaEvent |
| US7-T6 | Expert:innen-Empfehlungs-API | S | US7-T3 | Endpoint: gibt Top-N User für Topic X (sortiert nach `karmaInTopicActive`) zurück |
| US7-T7 | Integration in Q&A-Flow (US-2 Vorbereitung) | XS | US7-T6 | Hook in Question-Service: liefert `suggestedExperts` aus US7-T6 |
| US7-T8 | Karma-Transparenz-View | S | F-4 | "Wie habe ich meine Karma verdient?" – Liste aller `KarmaEvent` für User mit Quelle |
| US7-T9 | Level-Up-Notifications | XS | F-8, US7-T3 | Notification bei Level-Wechsel (Novice → Contributor → Expert) |
| US7-T10 | Anti-Gaming-Mechanismen | S | US7-T2, US7-T5 | Rate-Limiting für PeerEndorsement, Selbst-Endorsement blocken, Detection auffälliger Muster |
| US7-T11 | E2E-Tests US-7 | S | alle US7-T* | Szenarien: Beitrag erstellen → Karma erhalten → Profil aktualisiert → Level-Up |

**Empfohlene Sequenz:** T1 → T2 → T4 → T5 → T8 → T10 → T3 → T6 → T9 → T11 (T7 erst mit US-2)

---

## Cross-Story-Abhängigkeiten (kritischer Pfad)

```
F-1, F-2, F-3, F-4, F-5  (parallel, Sprint 0–1)
        │
        ▼
F-6 (Konnektoren) ────► US-5-Beiträge können auch externe Quellen ergänzen
        │
        ▼
US5-T1, T5, T7 ──────► US7-T1, T2 ──────► US3-T5 (Review-Workflow teilt sich Backend-Pattern mit US-5)
        │                    │                    │
        ▼                    ▼                    ▼
US5-T2 (UI)            US7-T4 (Profil)       US3-T6 (Dashboard)
        │                    │                    │
        └────────────────────┴────────────────────┘
                             ▼
                    Integration & E2E
```

**Kritischer Pfad:** F-1 → F-3 → US5-T1 → US5-T5 → US7-T2 → US3-T5
→ ohne diese Kette gibt es kein funktionierendes MVP.

---

## Sprint-Vorschlag (4 Sprints à 2 Wochen, Annahme: 2 BE + 1 FE + 1 KI)

### Sprint 0 (Foundation)
F-1, F-2, F-3, F-4, F-5

### Sprint 1 (Beiträge erstellen)
F-6 (Start), US5-T1, US5-T2, US5-T5, US5-T7, US5-T8, US7-T1

### Sprint 2 (Karma & Review)
US7-T2, US7-T4, US7-T5, US7-T8, US5-T6, US5-T10, US3-T1, US3-T2, US3-T4

### Sprint 3 (Erkennung & Konsolidierung)
US3-T5, US3-T6, US3-T7, US3-T8, US7-T3, US7-T6, US7-T9, US7-T10, F-8, F-10

### Sprint 4 (KI-Komponente, Polish & Testing)
US3-T3 (Widerspruchserkennung), US5-T3 (Audio), US5-T4 (Annotation), US5-T9 (Topic-Konsolidierung), alle E2E-Tests, Bug-Fixing

---

## Risiken & Beobachtungen

| Risiko | Auswirkung | Empfehlung |
|---|---|---|
| **US3-T3 (Widerspruchserkennung via LLM) unterschätzt** | KI-Qualität entscheidet über Akzeptanz von US-3 | Spike vorab (1 Woche), False-Positive-Rate messen, ggf. erst manuelle + Age-Trigger im MVP |
| **F-6 (Konnektoren) komplexer als gedacht** | Ohne Sync ist Plattform leer | Mit *einer* Quelle starten (z.B. nur Confluence), andere Quellen iterativ |
| **US7-T10 (Anti-Gaming) wird vergessen** | Karma-System wird nicht ernst genommen | Nicht erst nach Launch denken – early einbauen |
| **Topic-Konsolidierung (US5-T9) skaliert nicht** | Unkontrollierte Tag-Wildwuchs | Klare Governance: alle 4 Wochen Topic-Review durch Admin |
| **Datenschutz/AI-Governance** | DSGVO/AI-Act-Verstoß | Frage 5 aus Eingangsfragenkatalog noch offen – muss vor Sprint 0 geklärt sein! |

---

## Definition of Done (für alle Tasks)

- Code reviewed (4-Augen-Prinzip)
- Unit-Tests > 80% Coverage
- API-Dokumentation aktualisiert (OpenAPI/Swagger)
- Audit-Logging implementiert wo relevant
- Monitoring-Metriken exportiert
- Auf Staging deployt und manuell verifiziert
- DSGVO-Check: keine personenbezogenen Daten ungewollt geloggt

---

Möchtest Du als Nächstes:
1. **Sprint-Planung detaillieren** (Story Points, Velocity-Annahmen, Team-Setup)?
2. Das **Sequenzdiagramm "Beitrag erstellen → Review → Karma vergeben"** zeichnen?
3. Einen **Risiko-Workshop** zu den oben genannten Punkten vorbereiten (z.B. zur LLM-Widerspruchserkennung)?
4. Die noch offene **Frage 5 (DSGVO/AI-Governance)** vertiefen, da sie laut Risiko-Tabelle vor Sprint 0 geklärt sein muss?



<font color="cornflowerblue">
</font>

