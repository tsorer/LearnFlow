# ADR-004: LLM-Provider & Abstraktion — LiteLLM (MVP: OpenAI Direct, Produktion: Azure OpenAI EU)

| Feld | Inhalt |
|---|---|
| **Status** | Proposed |
| **Datum** | 2026-05-27 |
| **Aktualisiert** | 2026-05-31 — MVP-Prämisse (keine echten internen Dokumente) eingearbeitet |
| **Verfasser** | LearnFlow-Team (Frank, Niklaus, Reto, Christoph) |

---

## Kontext

Die RAG-Pipeline sendet Dokumentchunks als Kontext an den LLM. Die Wahl des Providers beeinflusst Kosten, Qualität und Datenschutz direkt.

**MVP-Prämisse (massgeblich für diese Entscheidung):** Im MVP wird **kein echter interner Dokumentenbestand** verarbeitet — der Korpus besteht ausschliesslich aus Test-, Dummy- bzw. öffentlich unbedenklichen Inhalten. Datenschutz ist im MVP daher **kein Blocker**, und es darf der einfachste, am schnellsten verfügbare Provider verwendet werden.

**Produktion ist davon getrennt:** Sobald echte interne Unternehmensdokumente verarbeitet werden, gilt die Datenschutz-Linie aus ADR-001 — ein Upload an einen US-Endpunkt ohne Datenschutzprüfung verstösst gegen unternehmensweite Richtlinien. Der Produktiv-Pfad muss deshalb EU-/datenschutzkonform sein. Die Maintainability-NFA verlangt, dass dieser Wechsel ohne Code-Change möglich ist. Für Umgebungen, in denen Daten die lokale Infrastruktur gar nicht verlassen dürfen, steht **Ollama** bereit; LiteLLM macht jeden dieser Wechsel zu einem einzigen Konfigurationseintrag.

---

## Entscheidung

Wir verwenden **LiteLLM** als Abstraktions-Layer und stufen den Provider nach Datensensibilität:

- **MVP-Default: OpenAI Direct** (`api.openai.com`) — einfachste Anbindung: nur ein `OPENAI_API_KEY`, kein Azure-Setup, keine Quota-Genehmigung, kein Deployment-Name. Zulässig, weil im MVP keine echten internen Dokumente verarbeitet werden.
- **Vor Verarbeitung echter interner Dokumente (Produktion/Post-MVP): Azure OpenAI EU** — EU-Datenresidenz, kein Drittland-Transfer, abrechenbar über das bestehende Azure-Enterprise-Agreement. Umstellung = **eine Konfigurationszeile** (LiteLLM-`model`-String + Credentials).
- **Ollama (lokal)** für Deployments, in denen Daten die eigene Infrastruktur gar nicht verlassen dürfen — und als Cloud-key-freie Entwicklungs-/Testumgebung.
- Modell: `gpt-4o-mini` als Standard (kosteneffizient, ausreichend für RAG-Antworten); `gpt-4o` als konfigurierbarer Upgrade-Pfad.

| Umgebung | Provider | Modell |
|---|---|---|
| **MVP / Standard** (keine echten internen Dokumente) | **OpenAI Direct** | `gpt-4o-mini` |
| Produktion (echte interne Dokumente) | Azure OpenAI EU | `gpt-4o-mini` |
| Datenschutz / OnPrem | Ollama (lokal) | `llama3.2` oder `mistral` |

---

## Konsequenzen

### Positive Konsequenzen

- **+** **Sofort einsatzbereit:** OpenAI Direct braucht nur einen API-Key — kein Azure-Setup, keine Quota-Wartezeit. Maximale Geschwindigkeit für Spike und MVP.
- **+** LiteLLM erfüllt die Maintainability-NFA direkt: Wechsel OpenAI Direct ↔ Azure OpenAI EU ↔ Ollama ist ein Konfigurationseintrag, kein Code-Change, kein Deployment.
- **+** Der EU-/Compliance-Pfad ist vorab entschieden und dokumentiert — die Umstellung vor dem ersten echten Dokument ist ein bekannter, kleiner Schritt statt einer offenen Frage.
- **+** `gpt-4o-mini` ist kosteneffizient; über OpenAI Direct und Azure stehen dieselben Modelle bereit, d. h. die Umstellung ändert die Antwortqualität nicht.
- **+** Ollama erlaubt Entwicklung/Testing vollständig ohne Cloud-Key und deckt zugleich den maximalen Datenschutz-Fall ab.

### Negative Konsequenzen

- **−** **Zwingende Umstellung vor Produktivdaten:** OpenAI Direct verarbeitet Daten auf US-Servern. Wird die Umstellung auf Azure OpenAI EU vor dem ersten echten internen Dokument vergessen, entsteht ein Compliance-Verstoss. **Mitigation:** harte Vorbedingung im Go-Live-Checklist; optional ein Guard, der bei als „intern/produktiv" markiertem Korpus einen Nicht-EU-Provider ablehnt.
- **−** Der Azure-Setup-Aufwand (Subscription, Modell-Deployment, ggf. Quota-Genehmigung, Grössenordnung 2–4 Wochen) verschiebt sich nur — er muss rechtzeitig **vor** dem Produktivbetrieb mit echten Daten eingeplant werden, nicht erst bei Bedarf.
- **−** Laufende API-Kosten pro Anfrage. Für < 30 Pilotnutzer überschaubar, aber nicht im 360 h Personalbudget enthalten.
- **−** Bei Provider-Ausfall kein automatisches Failover. Mitigation: LiteLLM-Fallback (z. B. auf Ollama) konfigurierbar; für den Pilot reicht eine kontrollierte Fehlermeldung (Reliability-NFA).

---

## Abgewogene Alternativen

| Alternative | Warum verworfen |
|---|---|
| **Azure OpenAI EU als MVP-Default** | EU-konform und produktionsreif, aber der einmalige Setup-/Quota-Aufwand (2–4 Wochen) bremst den Spike unnötig — solange im MVP keine echten internen Dokumente verarbeitet werden, bringt er keinen Schutzwert. Bleibt der **Produktiv-Pfad**, nur nicht der MVP-Start. |
| **OpenAI Direct auch in Produktion (mit echten Daten)** | Bequem, aber US-Datenverarbeitung interner Dokumente verstösst gegen die Datenschutz-Linie (ADR-001). Nur zulässig, solange keine echten internen Dokumente im Spiel sind. |
| **Ollama (vollständig OnPrem als einzige Option)** | Maximaler Datenschutz, keine Kosten. Verworfen als Standard, weil die Qualität lokaler Modelle für komplexe Domänenfragen schlechter ist als `gpt-4o-mini`; bleibt explizit als Datenschutz-/OnPrem-Konfiguration vorgesehen. |
| **Anthropic Claude (via AWS Bedrock EU)** | Qualitativ konkurrenzfähig und über Bedrock in EU-Regionen mit Datenresidenz betreibbar — also ein valider EU-konformer Produktiv-Alternativpfad. Zugunsten Azure OpenAI EU zurückgestellt wegen bestehender Azure-Enterprise-Anbindung und Konsistenz mit ADR-001. Dank LiteLLM jederzeit ohne Architektur-Entscheid umstellbar. |

---

*Abhängigkeiten: ADR-001 (Modularer Monolith), ADR-002 (FastAPI) · Verbunden: ADR-005 (Embedding-Modell — gleiche MVP-/Produktiv-Staffelung)*
