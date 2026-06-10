Erstelle ein C4 Container Diagram für LearnFlow.

**Projektname:** LearnFlow
**Beschreibung:** Interne Lernplattform, die neuen Entwickler:innen, Requirements-Engineers und Tester:innen das Domänen- und Systemwissen historisch gewachsener Fachanwendungen über quellenbasierte KI-Antworten und überprüfte Quizfragen zugänglich macht – auf Basis eines kuratierten, fachbereichs-freigegebenen Lern-Korpus.

---

## Top 3 Quality Attributes (aus Übung 1):

1. **Reliability** – Halluzinationsrate = 0 %; Out-of-Corpus-Erkennungsrate ≥ 90 % „Weiss ich nicht"; Ausfall des LLM-Service führt immer zu kontrollierter Fehlermeldung, nie zu generiertem Fallback-Text.
2. **Security** – Kein Zugriff ohne Authentifizierung; RBAC (Lernende / Bereichsverantwortlicher / Admin); personenbezogene Daten verlassen die EU nicht (DSGVO); Auth-Schicht SSO-nachrüstbar ohne Umbau.
3. **Maintainability** – Alle Schwellenwerte (Konfidenz, Stale, Cluster-Mindestgrösse) in DB änderbar ohne Deployment; LLM-Provider wechselbar per Konfigurationseintrag (LiteLLM-Abstraktion); modulare RAG-Komponenten ohne Ripple-Effects.

---

## Systemübersicht aus C1:

**Nutzertypen:** Neue Entwickler:in · Requirements-Engineer · Tester:in · Fachbereich/Kuration · Admin

**Externe Systeme:**
- LLM / KI-API (z.B. Anthropic, Azure OpenAI)
- Dokumentenspeicher / Korpus-Verwaltung (z.B. SharePoint, Confluence)
- SSO / Identity Provider (z.B. Azure AD / Entra ID)
- Benachrichtigungssystem (Teams)

---

## Fragen:

1. Welche Container brauchen wir? (Web App, API, DB, Cache, Worker?)
2. Welche Technologien passen zu unserem Team und unseren QAs?
3. Wie kommunizieren die Container miteinander?
4. Begründe jeden Container in einem Satz, direkt bezogen auf unsere Top-3-QAs.

---

**Unser Team:** 2–3 Devs, ca. 3 Monate (320–480 h total), gemischter Background (kein reines Frontend- oder Backend-Team).

**Constraints:**
- MVP: < 30 gleichzeitige Nutzer, Single-Instance, kein HA-Bedarf
- Architektur muss Multi-Bereich-Ausbau erlauben ohne Redesign (stateless Services)
- LLM-Provider (Cloud vs. OnPrem/Ollama) per Konfiguration wechselbar
