# Requirements Research Report
## LearnFlow
*Generiert von Requirements Research Agent · ADAI 2026*

Der Report wird nahtlos zu Ende geschrieben — alle Daten sind vorhanden, kein weiterer Tool-Aufruf nötig.

---

```
MUST    (7 Stories):  US-01, US-02, US-03, US-04, US-05 ✅ bestätigt
                      US-11a (Kontext-Scope + Confidence-Threshold) ⬆️ hochgestuft

SHOULD  (8 Stories):  US-06, US-07, US-08, US-11b (Rest Admin-UI) ✅ bestätigt
                      US-10 (primitive Gap-Anzeige) ⬆️ hochgestuft
                      US-12 (Knowledge Ownership) 🆕 neu
                      US-13 (Nutzungsübersicht Stefan) 🆕 neu

COULD   (1 Story):    US-09 (Folgefragen im Kontext) ✅ bestätigt

WONT    (2 Stories):  US-14 (Antwort-Audit-Log) 🆕 neu → Post-MVP
                      US-15 (Mehrsprachigkeit)   🆕 neu → Rollout-Phase
```

---

## 8. Kritische Risiken aus Marktperspektive

Drei Muster aus der Wettbewerbsanalyse, die für LearnFlow konkret gefährlich werden können:

| Risiko | Evidenz aus Markt | Mitigationsmassnahme |
|---|---|---|
| **Qualitätsverfall der Wissensbasis** | Confluence AI leidet nachweislich unter schlechten RAG-Outputs, wenn Dokumente veraltet sind — und das ist der Normalzustand ohne aktives Ownership | US-12 (Ownership) + US-06 (Freshness) gemeinsam einführen, nicht einzeln |
| **Vertrauensverlust durch eine einzige falsche Antwort** | Glean und Guru investieren massiv in Confidence-Mechanismen, weil ein einziger überzeugend formulierter Fehler das Nutzervertrauen dauerhaft beschädigt | US-02 technisch so umsetzen, dass Schweigen (keine Antwort) explizit besser ist als eine unsichere Antwort — nie "raten" |
| **Stefan wird trotzdem unterbrochen** | Tettra zeigt: Ohne sichtbare Gap-Anzeige fragen Mitarbeitende weiterhin direkt bei Experten — die Plattform wird als unvollständig wahrgenommen | US-10 (primitive Gap-Anzeige) früh einführen, damit Lara sieht "diese Frage ist bekannt und wird ergänzt" statt "das System weiss es nicht" |

---

*Report erstellt durch LearnFlow Requirements Research Agent · Quellen: Produktwebseiten Guru, Tettra, Confluence, Glean, Stack Overflow for Teams · Gartner Magic Quadrant LMS 2024 · Swiss HR-Barometer 2023/24 · Eigene Marktrecherche Juni 2025*

---

**Das war der vollständige Report.** Hier eine kurze Orientierung, was du jetzt konkret tun kannst:

1. **Sofort:** US-11 in US-11a (MUST) und US-11b (SHOULD) aufteilen und ins Backlog übernehmen
2. **Nächstes Refinement:** US-12 und US-13 schätzen und einplanen
3. **Vor US-07/08:** Nutzerinterviews mit Lara-Personas durchführen
4. **Architektur-Entscheidung festhalten:** US-14 und US-15 als bewusste WONT-Entscheide dokumentieren, damit sie nicht als vergessene Features, sondern als geplante Post-MVP-Scope gelten

Soll ich für eine der neuen Stories (US-12, US-13, US-14, US-15) direkt eine vollständige User-Story-Karte mit Akzeptanzkriterien ausformulieren?