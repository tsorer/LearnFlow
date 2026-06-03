# ADR-004: LLM-Provider & Abstraktion — Azure OpenAI EU + LiteLLM

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto) |

---

## Kontext

Die RAG-Pipeline sendet Dokumentchunks als Kontext an den LLM. Die Wahl des Providers beeinflusst Kosten, Qualität und Datenschutz direkt. **Massgeblich ist hier der Datenschutz:** LearnFlow verarbeitet interne Unternehmensdokumente, deren Upload an einen US-Endpunkt ohne explizite Datenschutzprüfung gegen unternehmensweite Richtlinien verstösst (konsistent mit der Stack-Grundlage in ADR-001). Der Produktiv-Default muss daher die EU-/datenschutzkonforme Variante sein, nicht eine US-Cloud. Die Maintainability-NFA verlangt zusätzlich, dass ein Provider-Wechsel ohne Code-Change möglich ist. Für Umgebungen mit maximalen Datenschutzanforderungen — wenn Daten die lokale Infrastruktur gar nicht verlassen dürfen — steht **Ollama als vollständig lokale Lösung** bereit; LiteLLM macht jeden dieser Wechsel zu einem einzigen Konfigurationseintrag.

---

## Entscheidung

Wir verwenden **Azure OpenAI EU** als Produktiv-Provider mit **LiteLLM** als Abstraktions-Layer.

- Modell: `gpt-4o-mini`-Deployment als Standard (kosteneffizient, ausreichend für RAG-Antworten); `gpt-4o` als konfigurierbarer Upgrade-Pfad.
- Datenresidenz: Verarbeitung in europäischen Azure-Rechenzentren — kein Drittland-Transfer der Dokument-Chunks, abrechenbar über bestehendes Azure-Enterprise-Agreement.
- LiteLLM normalisiert die API über Provider-Grenzen hinweg — Wechsel zwischen Azure OpenAI EU, OpenAI Direct (Dev) und Ollama ist eine Konfigurationsänderung, kein Code-Change.
- **OpenAI Direct** (api.openai.com) bleibt ausschliesslich für Entwicklung/Tests *ohne Produktivdaten* zugelassen; **Ollama (lokal)** für Deployments, in denen Daten die eigene Infrastruktur gar nicht verlassen dürfen.

| Umgebung | Provider | Modell |
|---|---|---|
| Standard / Produktion | Azure OpenAI EU | `gpt-4o-mini` |
| Entwicklung / Test (keine Produktivdaten) | OpenAI Direct | `gpt-4o-mini` |
| Datenschutz / OnPrem | Ollama (lokal) | `llama3.2` oder `mistral` |

---

## Konsequenzen

### Positive Konsequenzen

- **+** Datenschutz-Compliance by Default: Produktivdaten bleiben in europäischen Rechenzentren — kein Drittland-Transfer, kein Widerspruch zu unternehmensweiten Richtlinien (vgl. ADR-001).
- **+** LiteLLM erfüllt die Maintainability-NFA direkt: Provider-Wechsel (Azure EU ↔ OpenAI Direct ↔ Ollama) ist ein Konfigurationseintrag, kein Code-Change, kein Deployment.
- **+** `gpt-4o-mini` ist kosteneffizient bei vergleichbarer RAG-Qualität für strukturierte Dokument-Fragen — über Azure dieselben Modelle wie bei OpenAI Direct.
- **+** Abrechnung über bestehendes Azure-Enterprise-Agreement statt separatem API-Vertrag.
- **+** Ollama als lokale Datenschutz-Lösung: für Deployments mit der Anforderung, dass Daten die Infrastruktur gar nicht verlassen, ist der Umstieg nahtlos — gleicher Code. Entwicklung/Testing laufen zudem vollständig ohne Cloud-Key via Ollama.

### Negative Konsequenzen

- **−** Einmaliger Setup-Aufwand: Azure-Subscription, Deployment der Modelle und ggf. Quota-Genehmigung (Grössenordnung 2–4 Wochen) müssen vor Go-Live eingeplant werden. Mitigation: in der Spike-Phase über OpenAI Direct (ohne Produktivdaten) entwickeln, parallel das Azure-Deployment beantragen.
- **−** Laufende API-Kosten pro Anfrage. Für < 30 Pilotnutzer überschaubar, aber nicht im 360 h Personalbudget enthalten. Azure-Quotas/Rate-Limiting vor Go-Live konfigurieren.
- **−** Geringfügig höhere Latenz durch EU-Routing gegenüber US-Endpunkten — im Rahmen der Performance-NFA (≤ 10 s @ p95) unkritisch.
- **−** Bei Provider-Ausfall kein automatisches Failover. Mitigation: LiteLLM-Fallback (z. B. auf Ollama) konfigurierbar; für den Pilot reicht eine kontrollierte Fehlermeldung (Reliability-NFA).

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **OpenAI Direct (api.openai.com) als Produktiv-Default** | Sofort einsatzbereit mit API-Key, kein Azure-Setup. Verworfen als Produktiv-Default, weil Daten auf US-Servern verarbeitet werden — kein EU-Datenhaltungs-Guarantee, Widerspruch zur Datenschutz-Linie (ADR-001). Der einmalige Azure-Setup-Aufwand wiegt die dauerhafte Compliance-Anforderung nicht auf. Bleibt als Dev-/Test-Pfad ohne Produktivdaten zugelassen. |
| **Ollama (vollständig OnPrem als einzige Option)** | Maximaler Datenschutz, keine Kosten. Verworfen als Standard, weil die Qualität lokaler Modelle für komplexe Domänenfragen schlechter ist als `gpt-4o-mini`; bleibt explizit als Datenschutz-/OnPrem-Konfiguration vorgesehen. |
| **Anthropic Claude (via AWS Bedrock EU)** | Qualitativ konkurrenzfähig und über Bedrock in EU-Regionen mit Datenresidenz betreibbar — also ein *valider* EU-konformer Alternativ-Default. Verworfen zugunsten Azure OpenAI EU nur wegen der bestehenden Azure-Enterprise-Anbindung (Abrechnung/Setup) und der Konsistenz mit ADR-001. Dank LiteLLM jederzeit ohne Architektur-Entscheid umstellbar, falls sich Konditionen/Qualität verschieben. |

---

*Abhängigkeiten: ADR-001 (Modularer Monolith), ADR-002 (FastAPI) · Nächste ADRs: ADR-005 (Embedding-Modell)*
