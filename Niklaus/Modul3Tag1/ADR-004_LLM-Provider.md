# ADR-004: LLM-Provider & Abstraktion — OpenAI API + LiteLLM

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

Die RAG-Pipeline sendet Dokumentchunks als Kontext an den LLM. Die Wahl des Providers beeinflusst Kosten, Qualität und Datenschutz direkt. Die Maintainability-NFA verlangt, dass ein Provider-Wechsel ohne Code-Change möglich ist. Für Umgebungen mit strengen Datenschutzanforderungen — wenn Daten die lokale Infrastruktur nicht verlassen dürfen — steht **Ollama als vollständig lokale Lösung** bereit; LiteLLM macht diesen Wechsel zu einem einzigen Konfigurationseintrag.

---

## Entscheidung

Wir verwenden **OpenAI API** (api.openai.com) mit **LiteLLM** als Abstraktions-Layer.

- Modell: `gpt-4o-mini` als Standard (kosteneffizient, ausreichend für RAG-Antworten); `gpt-4o` als konfigurierbarer Upgrade-Pfad.
- LiteLLM normalisiert die API über Provider-Grenzen hinweg — Wechsel auf Ollama ist eine Konfigurationsänderung, kein Code-Change.
- Bei Datenschutzanforderungen wird auf **Ollama (lokal)** umgestellt: keine Daten verlassen die eigene Infrastruktur.

| Umgebung | Provider | Modell |
|---|---|---|
| Standard / Produktion | OpenAI API | `gpt-4o-mini` |
| Datenschutz / OnPrem | Ollama (lokal) | `llama3.2` oder `mistral` |

---

## Konsequenzen

### Positive Konsequenzen

- **+** Kein Azure-Setup, kein Quota-Genehmigungsprozess — sofort einsatzbereit mit API-Key.
- **+** LiteLLM erfüllt die Maintainability-NFA direkt: Provider-Wechsel auf Ollama ist ein Konfigurationseintrag, kein Code-Change, kein Deployment.
- **+** `gpt-4o-mini` ist kosteneffizient bei vergleichbarer RAG-Qualität für strukturierte Dokument-Fragen.
- **+** Ollama als lokale Datenschutz-Lösung: für Deployments ohne Cloud-Anbindung oder mit Anforderung, dass Daten lokal bleiben, ist der Umstieg nahtlos — gleicher Code.
- **+** Entwicklung und lokales Testing laufen vollständig ohne API-Key via Ollama.

### Negative Konsequenzen

- **−** OpenAI verarbeitet Daten auf US-Servern — kein EU-Datenhaltungs-Guarantee. Mitigation: für datenschutzkritische Deployments auf Ollama (lokal) umstellen (eine Konfigurationszeile).
- **−** Laufende API-Kosten pro Anfrage. Für < 30 Pilotnutzer überschaubar, aber nicht im 360 h Personalbudget enthalten.
- **−** Bei OpenAI-Ausfall kein automatisches Failover. Mitigation: LiteLLM-Fallback auf Ollama konfigurierbar; für den Pilot reicht eine kontrollierte Fehlermeldung (Reliability-NFA).

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Azure OpenAI EU** | EU-Datenhaltung garantiert, aber Quota-Genehmigung dauert 2–4 Wochen und erfordert Azure-Subscription-Setup. Kein Qualitätsvorteil gegenüber OpenAI Direct bei gleichen Modellen. |
| **Ollama (vollständig OnPrem als einzige Option)** | Maximaler Datenschutz, keine Kosten. Verworfen als Standard weil Qualität lokaler Modelle für komplexe Domänenfragen schlechter als `gpt-4o-mini`; bleibt explizit als Datenschutz-Konfiguration vorgesehen. |
| **Anthropic Claude API** | Vergleichbare Qualität. LiteLLM ermöglicht späteren Wechsel ohne Architektur-Entscheid — kein Grund, heute zu wechseln. |

---

*Abhängigkeiten: ADR-001 (Modularer Monolith), ADR-002 (FastAPI) · Nächste ADRs: ADR-005 (Embedding-Modell)*
