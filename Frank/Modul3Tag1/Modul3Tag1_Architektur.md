
| CAS Application Development with AI (ADAI) · 2026 Modul 3 · Tag 1  —  Übungen: Architektur mit AI | BFH Biel · Ilja Rasin |
| --- | --- |


Architektur mit AI — Drei Übungen
Heute wendet ihr Architektur-Konzepte direkt auf euer eigenes Projekt an. Jede Übung baut auf der vorherigen auf.

| Ü1 09:15–10:00 Quality Attributes Von Requirements zur Architektur | Ü2 10:15–11:00 ADR schreiben Eure erste Architektur-Entscheidung | Ü3 11:15–12:00 C4 Diagramme Context + Container für euer Projekt |
| --- | --- | --- |



| Ü1 | Quality Attributes für euer Projekt   ·   09:15 – 10:00 Welche nicht-funktionalen Anforderungen treiben eure Architektur? |
| --- | --- |


Quality Attributes (QA) sind nicht-funktionale Anforderungen — sie bestimmen WIE das System funktioniert, nicht WAS es tut. Sie sind die eigentlichen Architektur-Treiber.

**Die wichtigsten Quality Attributes — Kurzreferenz**


| QA | Was es bedeutet | Typische Architektur-Konsequenz |
| --- | --- | --- |
| Performance | Wie schnell antwortet das System? | Caching · CDN · Async Processing |
| Scalability | Wie viele gleichzeitige Nutzer? | Stateless Services · Load Balancer |
| Security | Wie schützen wir Daten? | Auth Service · Encryption · Audit Log |
| Reliability | Wie verfügbar ist das System? | Health Checks · Retry Logic · Monitoring |
| Maintainability | Wie einfach ist es zu ändern? | Modulare Struktur · Klare Boundaries |
| Testability | Wie gut ist es testbar? | Dependency Injection · Interfaces |


Teil 1 · Quality Attributes identifizieren (15 Min)
Schaut eure Requirements aus Modul 2 an. Welche QAs sind für euer Projekt relevant?

> **Hinweis NFA vs. FA:** Quality Attributes sind nicht-funktionale Anforderungen — sie beschreiben WIE das System sein muss, nicht WAS es tut. In der Requirements-Spalte stehen daher messbare Qualitätskriterien (NFAs). US-Nummern dienen als Quellenangabe, sind aber selbst funktionale Anforderungen (FAs) und keine QA-Treiber.

| Quality Attribute | Nicht-funktionale Anforderung (NFA) — messbar & beobachtbar | Warum wichtig für uns? |
| --- | --- | --- |
| Performance | **Antwortzeit ≤ 10 s am 95. Perzentil** unter Normallast · Dokument nach Upload innerhalb von **≤ 5 Minuten** als Quelle verfügbar · Antwort-Streaming (Token-by-Token) erforderlich, da batch-Response träge wirkt *(abgeleitet aus FA: US-01, US-04)* | RAG-Pipeline (Retrieval + Embedding + LLM-Generierung) addiert Latenzen inhärent. Überschreitet die Wartezeit die Schwelle, bricht Lara ab und fragt wieder bei Stefan nach — das Kernversprechen entfällt. |
| Scalability | **Maximale Gleichzeitigkeit im MVP: < 30 Nutzer**, 1 Pilot-Bereich hartcodiert · Architektur muss Multi-Bereich-Ausbau ermöglichen **ohne Redesign** (stateless Services, kein shared State) *(MVP-Constraint; Post-MVP Out of Scope)* | Kein Skalierungsdruck heute — aber eine zustandsbehaftete Architektur würde den Post-MVP-Ausbau auf mehrere Bereiche zu einem vollständigen Umbau machen. |
| Security | **Kein Systemzugriff ohne gültige Authentifizierung** · Jede Ressource erfordert rollenbasierte Autorisierung (Lernende / Bereichsverantwortlicher / Admin) · **Personenbezogene Daten verlassen die EU nicht** (DSGVO) · Feedback und Query-Logs werden pseudonymisiert gespeichert · Cluster < 5 Fragen werden nicht angezeigt (Re-Identifikationsschutz) · Auth-Basis SSO-nachrüstbar ohne Umbau *(abgeleitet aus FA: US-05, US-11, US-03, US-10)* | Interne Unternehmensdokumente und Fachprozesse sind schützenswert. DSGVO-Compliance ist im Schweizer Enterprise-Umfeld nicht verhandelbar. Eine einmalige Datenpanne beendet den Piloten. |
| Reliability | **Halluzinationsrate = 0 %**: Das System darf niemals eine Antwort ohne valide, belegbare Quellenreferenz ausgeben · Ausfall des LLM-Service darf **nie** zu einer generierten Fallback-Antwort führen — kontrollierte Degradation (Fehlermeldung) ist Pflicht · Out-of-Corpus-Erkennungsrate: ≥ 90 % „Weiss ich nicht" *(messbare Schwelle; abgeleitet aus FA: US-01, US-02; Risiko 3)* · **MVP bewusst: kein HA-Setup**, Single-Instance, Business-Hours-Nutzung *(Kontroverse: → Teil 2)* | Eine halluzinierte Antwort mit echter Quellenangabe ist unsichtbar — Lara merkt es nicht, handelt falsch, verliert Vertrauen erst Wochen später. Das ist existenziell für den Pilot, unabhängig von der Nutzerzahl. |
| Maintainability | **Alle Konfigurationsparameter** (Konfidenz-Schwellenwert, Stale-Schwellenwert, Cluster-Mindestgrösse) müssen **ohne Code-Deployment und ohne Systemstart** geändert werden können · **LLM-Provider wechselbar durch Konfiguration** — kein Code-Change (LiteLLM-Abstraktion) · Jede RAG-Komponente austauschbar ohne Seiteneffekte auf andere Module *(abgeleitet aus FA: US-02, US-06, US-11)* | 320–480 h Gesamtbudget. Jede Stunde für operative Anpassungen fehlt bei der Kernentwicklung. Provider-Wechsel (Cloud vs. OnPrem) muss ohne Entwickler-Eingriff möglich sein — sonst ist es ein Vertriebshindernis. |
| Testability | **Out-of-Corpus-Erkennungsrate ≥ 90 %** „Weiss ich nicht" als messbares Akzeptanzkriterium · **Halluzinationsrate messbar und regressionsfähig** bevor die Implementierung startet (Tech Spike als Go/No-Go) · Jede RAG-Komponente (Chunking, Embedding, Retrieval, Generierung) **einzeln isolierbar und testbar** · Konfidenz-Scoring-Mechanismus muss formal definiert sein, bevor er testbar ist *(abgeleitet aus: Risiko 1, Risiko 2, FA: US-02)* | RAG-Qualität ist ein empirisches Phänomen — nicht durch Code-Review validierbar. Ohne Testability weiss das Team nie, ob Reliability (Halluzinationsrate = 0 %) tatsächlich erreicht ist. |


Teil 2 · AI analysiert eure Quality Attributes (15 Min)
Prompt — fügt eure Requirements aus Modul 2 ein:

```
Hier sind unsere User Stories und Requirements: [EINFÜGEN]
Analysiere welche Quality Attributes für unser Projekt
am kritischsten sind.
Für die Top 3 QAs:
1. Warum ist dieser QA für unser Projekt besonders wichtig?
2. Welche konkreten architektonischen Massnahmen empfiehlst du?
3. Was passiert wenn wir diesen QA ignorieren?
Sei konkret — keine generischen Antworten.
Beziehe dich auf unser spezifisches Projekt.
```


**Ranking der drei Teammitglieder im Vergleich:**

| Rang | Frank | Nicklaus | Reto |
| --- | --- | --- | --- |
| 1 | Security | Reliability | Reliability |
| 2 | Maintainability | Testability | Security |
| 3 | Performance | Maintainability | Performance |

> **Reflexion: FA vs. NFA im Ranking**
> Frank, Nicklaus und Reto haben ursprünglich grösstenteils **funktionale Anforderungen** (User Stories US-xx) als Belege genannt — diese beschreiben WAS das System tut, nicht WIE gut. Bei der Neubewertung mit NFA-Brille (messbare Qualitätskriterien) verschiebt sich die Gewichtung: **Reliability** hat mit „Halluzinationsrate = 0 %" die härteste, existenziellste NFA des Projekts. **Security** hat mit der DSGVO-Pflicht eine nicht verhandelbare regulatorische NFA. **Performance** hat mit ≤ 10 s @ p95 eine klar messbare NFA. Franks ursprünglicher Reliability-Downgrade war auf eine FA-Perspektive gestützt (Uptime / HA-Setup) — unter NFA-Sicht bleibt die Korrektheitspflicht unabhängig von der Nutzerzahl bestehen.


**Top 3 QAs laut AI — NFA-gewichtet:**

1. **Reliability** *(NFA: Halluzinationsrate = 0 %, Out-of-Corpus ≥ 90 % „Weiss ich nicht")* — Die stärkste und existenziellste NFA des Projekts. Eine halluzinierte Antwort mit echter Quellenangabe ist unsichtbar und nicht reparierbar — Lara merkt es nicht, handelt falsch, das Vertrauen bricht. Diese NFA hängt nicht an der Nutzerzahl; sie gilt für den ersten Nutzer wie für den tausendsten. Das ist der Unterschied zu Uptime-Reliability (HA-Setup), die Frank bewusst zurückgestellt hat.
2. **Security** *(NFA: Kein unbefugter Zugriff; DSGVO — personenbezogene Daten verlassen die EU nicht)* — Regulatorische NFAs sind nicht verhandelbar. DSGVO-Verstoss ist kein technisches Risiko, sondern ein rechtliches. Interne Unternehmensdokumente im Korpus machen unbefugten Zugriff zu einem Business-Stopper. Die NFA „kein Zugriff ohne Authentifizierung und Autorisierung" ist binär — entweder erfüllt oder nicht.
3. **Maintainability** *(NFA: Konfigurationsparameter änderbar ohne Code-Deployment; LLM-Provider wechselbar ohne Code-Change)* — Die stärkste Budget-getriebene NFA. 320–480 h Gesamtbudget bedeutet: jede operative Stunde fehlt in der Entwicklung. Die NFA ist eindeutig messbar: Kann Stefan den Konfidenz-Schwellenwert ändern, ohne einen Entwickler zu rufen? Kann der LLM-Provider per Konfigurationseintrag gewechselt werden?


**Architektonische Massnahmen die wir umsetzen werden:**

- **Reliability:** Mehrschichtiger Unterdrückungsmechanismus (Quellenprüfung → Konfidenz-Score → Self-Check-Anteil). Circuit Breaker für LLM-Aufrufe (Timeout, HTTP 5xx, Quota). Fail-Safe als Designprinzip: „keine Antwort" ist immer besser als eine unsichere Antwort. Konfidenz-Schwellenwerte in der DB, nicht im Code — empirisch kalibrierbar nach Tech Spike.
- **Security:** JWT (8 h) + bcrypt-Hashing; Admin-Middleware für rollenbasierte Zugriffskontrolle; URL-Zugriff ohne Admin-Rolle wird serverseitig abgewiesen; Azure OpenAI EU (GDPR). Auth-Schicht so bauen, dass SSO später ohne Umbau nachrüstbar ist.
- **Maintainability:** Admin-UI für Threshold-Änderungen ohne Neustart; LiteLLM-Abstraktion für Modellwechsel via Config; Docker Compose für reproduzierbare Deployments; klare Modul-Grenzen ohne Ripple-Effects.
- **Performance:** Async Streaming-Response (FastAPI + React EventSource/SSE); pgvector HNSW-Index für schnelle Similarity-Suche; Dokument-Processing asynchron (Upload sofort bestätigt, Verarbeitung im Hintergrund). 10-Sek.-Limit als festes Akzeptanzkriterium in CI/CD-Tests verankern.
- **Testability:** Evaluationsdataset vor Sprint 1 (echte Dokumente, In-Corpus + Out-of-Corpus Fragen, erwartete Antworten). Automatisiertes Scoring im CI. LiteLLM ermöglicht A/B-Tests zwischen Providern mit identischer RAG-Pipeline.
- **Reliability (MVP-Entscheid):** Bewusst kein HA-Setup — Docker Compose Single Instance ist ausreichend für < 30 interne Nutzer. Post-MVP: Monitoring + Health Checks falls Nutzerzahl steigt.


Teil 3 · Teamdiskussion (10 Min)
Besprecht im Team:
- Stimmt ihr mit AI überein? Wo nicht — und warum?
- Welcher QA ist der schwierigste für euch technisch?
- Was würdet ihr an eurem Projekt ändern basierend auf dieser Analyse?


**Unser wichtigstes Takeout aus Übung 1:**

Reliability und Security sind die primären Architektur-Treiber — sensible interne Daten, GDPR-Pflicht und das Kernversprechen „quellenbelegte Antworten ohne Halluzinationen" lassen keinen Spielraum. Maintainability folgt direkt aus dem Budget-Constraint (320–480 h, 1 Tag/Woche). Performance ist ein hartes Akzeptanzkriterium (10 s @ p95), aber technisch lösbar. Die grösste Team-Diskussion: Ob Reliability ein MVP-Treiber ist (Nicklaus/Reto: ja, weil eine einzige falsche Antwort den Pilot kippt) oder bewusst zurückgestellt werden kann (Frank: Single-Instance für < 30 Nutzer akzeptabel).



| Ü2 | Architecture Decision Record schreiben   ·   10:15 – 11:00 Eure wichtigste Technologie-Entscheidung dokumentieren. |
| --- | --- |


Ein ADR dokumentiert eine Architektur-Entscheidung — damit zukünftige Entwickler verstehen warum so gebaut wurde. Ihr schreibt heute euer erstes echtes ADR.

**ADR-Format nach Michael Nygard — Kurzreferenz**


| Feld | Was hineingehört | Beispiel |
| --- | --- | --- |
| Titel | Kurze beschreibende Überschrift | ADR-001: PostgreSQL statt MongoDB |
| Status | Aktueller Stand | Proposed · Accepted · Deprecated |
| Kontext | Warum müssen wir entscheiden? | ACID-Compliance nötig für Buchungen |
| Entscheidung | Was haben wir entschieden — aktiv | Wir verwenden PostgreSQL |
| Konsequenzen | Was wird besser / schwieriger? | + ACID ✓  − Kein horizontales Sharding |


Teil 1 · Eure wichtigste Entscheidung identifizieren (10 Min)
Welche Technologie-Entscheidung ist für euer Projekt am kritischsten? Typische ADR-Kandidaten:

| Datenbank PostgreSQL vs MongoDB
vs SQLite vs Supabase | API-Stil REST vs GraphQL
vs gRPC | Architektur Monolith vs Modularer Monolith
vs Microservices |
| --- | --- | --- |



---

## ADR-001 · Reliability

**Titel:** Mehrschichtiger Halluzinations-Unterdrückungsmechanismus mit Faithfulness-Check

**Status:** Accepted

**Kontext — Warum müssen wir entscheiden?**

LearnFlow beantwortet Fachfragen mittels RAG. Ein LLM kann plausibel klingende, aber falsche Antworten erzeugen — auch bei vorhandener Quellenreferenz. Eine einzige halluzinierte Antwort beschädigt das Vertrauen nachhaltig. Das System muss schweigen statt raten. Ausserdem dürfen LLM-Ausfall und Quota-Überschreitung nie zu einer generierten Fallback-Antwort führen.

**Wichtige Einschränkung:** Kein Mechanismus eliminiert Halluzinationen vollständig. Stufe 1 und 2 messen Retrieval-Qualität, nicht Output-Korrektheit. Das Ziel ist eine nachweislich niedrige, messbare Fehlerrate — keine Null-Garantie.

**Abgewogene Alternativen:**

| Option | Beschreibung | Warum abgelehnt |
| --- | --- | --- |
| A · Kein Filter | LLM-Output direkt ausgeben | Halluzinationsrate unkontrolliert — nicht akzeptabel |
| B · Einfacher Konfidenz-Threshold | Ein Schwellenwert entscheidet | Grenzwertfälle nicht abgedeckt; ein Messwert ist zu fehleranfällig |
| C · LLM Self-Check | LLM schätzt eigene Antwortqualität ein | Self-reported confidence korreliert nachweislich schlecht mit tatsächlicher Korrektheit — abgelehnt |
| D · Zweistufig + Faithfulness-Check ✓ | Retrieval-Prüfung + separater Belegbarkeits-Check | Robuster: prüft Belegbarkeit statt Selbsteinschätzung; jede Stufe unabhängig kalibrierbar |

**Entscheidung — Was haben wir entschieden?**

Wir implementieren einen zweistufigen Unterdrückungsmechanismus mit anschliessendem Faithfulness-Check:

```
Stufe 1 · Quellenprüfung
  Bedingung : Treffer mit ausreichender Ähnlichkeit im Korpus
  Reaktion  : Kein Treffer → "Keine passende Quelle" — kein LLM-Aufruf

Stufe 2 · Konfidenz-Score (Retrieval)
  Bedingung : Retrieval-Score ≥ konfiguriertem Schwellenwert (in DB, nicht im Code)
  Reaktion  : Score < Schwellenwert → "Ich weiss es nicht sicher" — kein LLM-Aufruf
  Hinweis   : Schwellenwert ist modell- und korpusspezifisch — Neukalibrierung bei
              Provider-Wechsel zwingend (→ ADR-003)

Stufe 3 · Faithfulness-Check
  Methode   : Separater LLM-Prompt prüft: "Ist jede Aussage durch die Quelltexte belegbar?"
  Reaktion  : Nicht belegbar → Antwort unterdrückt, Quelltexte direkt angezeigt
  Hinweis   : Erfordert zweiten LLM-Aufruf — Latenzimpact auf 10s-SLA im Tech Spike messen.
              Falls SLA verletzt: Faithfulness-Check asynchron, Antwort nachträglich markiert.
```

Zusätzlich gilt ein Circuit Breaker für LLM-Ausfall: Timeout / HTTP 5xx / Quota → Fehlermeldung, niemals generierter Text.

| Positive Konsequenzen | Negative Konsequenzen |
| --- | --- |
| + Halluzinationsrisiko auf messbares Minimum reduziert (Out-of-Corpus ≥ 90 % "Weiss ich nicht") | − Keine Null-Garantie: Mechanismus reduziert, eliminiert nicht — muss im Onboarding kommuniziert werden |
| + Faithfulness-Check robuster als Self-Check: prüft Belegbarkeit statt Selbsteinschätzung | − Stufe 3 (zweiter LLM-Aufruf) erhöht Latenz — 10s @ p95 SLA muss im Tech Spike validiert werden |
| + Schwellenwert in DB: Stefan kalibriert ohne Deployment | − Schwellenwerte modell- und korpusspezifisch: bei Provider-Wechsel Neukalibrierung zwingend |
| + Jede Stufe unabhängig kalibrierbar, messbar, testbar | − Circuit Breaker separat implementieren und testen |
| + Erweiterbar ohne Redesign | |

---

## ADR-002 · Security

**Titel:** JWT + Argon2id als Authentifizierungsmechanismus, Auth-Layer SSO-vorbereitet

**Status:** Accepted

**Voraussetzung:** Sämtliche Kommunikation läuft ausschliesslich über HTTPS/TLS. JWT-Token über unverschlüsseltes HTTP zu übertragen würde die gesamte Auth-Architektur kompromittieren.

**Kontext — Warum müssen wir entscheiden?**

LearnFlow enthält interne Unternehmensdokumente — kein Zugriff ohne Authentifizierung und rollenbasierte Autorisierung. Im MVP: Accounts per DB-Script, kein Self-Service. Post-MVP: Azure AD / SAML SSO explizit geplant. Die SSO-Migration ist technisch nicht trivial (anderer Auth-Flow, andere Token-Formate) — die Auth-Kapselung begrenzt die Auswirkungen, eliminiert den Aufwand nicht. DSGVO verlangt EU-Datenhaltung: Auth-Lösung muss self-hosted betreibbar sein.

**Abgewogene Alternativen:**

| Option | Beschreibung | Warum abgelehnt |
| --- | --- | --- |
| A · Session-basierte Auth | Server-Side Sessions | Stateful → Skalierung erschwert; SSO-Integration aufwändig |
| B · JWT + Argon2id ✓ | Stateless Tokens, sicheres Hashing | Stateless, DSGVO-konform, SSO-Modul-Kapselung möglich |
| C · Auth-Plattform (Keycloak / Auth0) | Vollständige IAM-Lösung | MVP-Overhead; Auth0 US-Cloud (DSGVO-Risiko); Keycloak = eigener Betrieb |
| D · Direkt Azure AD | Unternehmens-SSO von Anfang an | Abhängigkeit von Kunden-IT; blockiert MVP ausserhalb eines Unternehmens |
| E · Opaque Tokens + Token Store | Revocation trivial per DB-Löschung | Für < 30 Nutzer vertretbar, aber Stateful — Komplexitätsvorteil von JWT geringer |

**Entscheidung — Was haben wir entschieden?**

Wir verwenden **JWT (4 h Gültigkeit) mit Argon2id**-Passwort-Hashing. Token werden als **HttpOnly Cookie** gesetzt (nicht in `localStorage`) — schützt vor XSS-basiertem Token-Diebstahl. JWT-Payload enthält ausschliesslich `user_id` und `role` — keine personenbezogenen Daten.

**Secret Management:** Das JWT-Secret wird als Umgebungsvariable injiziert — niemals im Repository. Bei Secret-Rotation werden alle aktiven Sessions beendet (Wartungsfenster erforderlich).

**Rollen-Entzug im Notfall:** Da JWTs stateless sind, wirkt ein Rollen-Entzug regulär erst nach Token-Ablauf (4 h). Für explizite Admin-Entzüge existiert ein minimaler Token-Blacklist-Eintrag in der DB — nur für Notfälle, nicht für reguläre Abläufe.

Der Auth-Layer ist ein gekapseltes Modul: Downstream-Code kennt nur das Interface. SSO-Migration Post-MVP bleibt auf dieses Modul beschränkt — bleibt aber ein eigenes Projekt.

| Positive Konsequenzen | Negative Konsequenzen |
| --- | --- |
| + Stateless, HttpOnly Cookie schützt vor XSS | − Reguläre Token-Revocation nicht möglich: Token gilt bis Ablauf (max. 4 h) |
| + Argon2id: OWASP-Standard 2022, resistent gegen GPU-Angriffe | − Kein Refresh-Token: Nutzerinnen melden sich alle 4 h neu an |
| + Notfall-Revocation via Token-Blacklist möglich | − Account-Verwaltung per DB-Script ist manuell |
| + SSO-Migration auf Auth-Modul beschränkt | − SSO-Migration ist kein trivialer Umbau: SAML-Flow und Token-Format unterscheiden sich fundamental |
| + Kein US-Cloud: vollständig self-hosted, DSGVO-konform | − Secret-Rotation beendet alle aktiven Sessions — Wartungsfenster nötig |

---

## ADR-003 · Maintainability

**Titel:** LiteLLM als LLM- und Embedding-Provider-Abstraktion

**Status:** Accepted

**Kontext — Warum müssen wir entscheiden?**

LearnFlow muss auf Cloud (Azure OpenAI, Claude) und OnPrem (Ollama, vLLM) laufen. Provider-Wechsel darf keinen Code-Change erfordern. 320–480 h Budget: jede Stunde für Migration fehlt im Kernprodukt. Tech Spike braucht A/B-Tests zwischen Providern mit identischer Pipeline.

**Kritische Einschränkungen:**
- **Provider sind nicht qualitativ gleichwertig:** Claude/GPT-4o liefern bessere Qualität als Llama 3.2 OnPrem. Die Schwellenwerte aus ADR-001 sind modellspezifisch — bei Provider-Wechsel ist Neukalibrierung zwingend.
- **Embedding-Wechsel invalidiert die gesamte Vektordatenbank:** Alle pgvector-Einträge sind modellspezifisch. Ein Wechsel des Embedding-Modells erfordert vollständiges Re-Embedding des Korpus — kein Hotfix, geplante Operation.

**Abgewogene Alternativen:**

| Option | Beschreibung | Warum abgelehnt |
| --- | --- | --- |
| A · Direkte SDK-Integration | Minimal, kein Overhead | Harter Lock-in; Wechsel = Refactoring im gesamten RAG-Stack |
| B · LangChain | Umfassende Abstraktion | Hoher Overhead, viel "Magic", schwer zu debuggen |
| C · LiteLLM ✓ | Leichtgewichtig, OpenAI-kompatibel | Minimal; LLM + Embeddings; aktiv maintained; gut debuggbar |
| D · Eigene Abstraktion | Volle Kontrolle | Maintenance-Last im kleinen Team nicht vertretbar |

**Entscheidung — Was haben wir entschieden?**

Wir verwenden LiteLLM für LLM-Generierung **und** Embeddings. Beide werden per Konfiguration gesteuert:

```
# LLM-Generierung
LLM_PROVIDER=claude              # Anthropic Claude (Cloud)
LLM_PROVIDER=azure/gpt-4o        # Azure OpenAI (Cloud, DSGVO-konform)
LLM_PROVIDER=ollama/llama3.2     # Ollama (OnPrem, Entwicklung / ressourcenarm)
LLM_PROVIDER=vllm/llama3.2       # vLLM (OnPrem, Produktion mit GPU-Infrastruktur)

# Embeddings — separat, da Wechsel Re-Embedding erfordert
EMBEDDING_PROVIDER=azure/text-embedding-3-small
EMBEDDING_PROVIDER=ollama/nomic-embed-text
```

**Embedding-Wechsel-Protokoll** (Pflicht bei Modellwechsel): (1) neues Modell kalibrieren, (2) Korpus neu einbetten, (3) pgvector-Index neu aufbauen, (4) ADR-001-Schwellenwerte neu kalibrieren.

LLM- und Embedding-Client per Dependency Injection — mockbar in Unit Tests. Streaming wird im Tech Spike pro Provider validiert.

| Positive Konsequenzen | Negative Konsequenzen |
| --- | --- |
| + LLM- und Embedding-Provider per Konfiguration wechselbar — kein Code-Change | − Embedding-Wechsel invalidiert alle Vektoren: Re-Embedding = geplante Operation, kein Hotfix |
| + Cloud vs. OnPrem: identische Codebase | − Schwellenwerte (ADR-001) modellspezifisch: Provider-Wechsel = Neukalibrierung zwingend |
| + A/B-Tests zwischen Providern im Tech Spike möglich | − LiteLLM: externe Abhängigkeit, Breaking Changes realistisch — Versionspinning + Changelog-Monitoring nötig |
| + Dependency Injection → beide Clients mockbar | − Streaming-Verhalten provider-spezifisch — pro Provider im Tech Spike validieren |
| + vLLM als OnPrem-Option für GPU-Infrastruktur explizit vorgesehen | − OnPrem-Qualität (Llama 3.2) < Cloud-Qualität (Claude/GPT-4o) — in Nutzerkommunikation transparent machen |




> ⚠️  Ein ADR pro grosser Entscheidung — nicht für alles. Weniger ist mehr.




| Ü3 | C4 Diagramme — Context + Container   ·   11:15 – 12:00 Visualisiert eure Architektur auf zwei Ebenen. |
| --- | --- |


Das C4 Model beschreibt Architektur in vier Zoom-Ebenen — wie Google Maps. Heute macht ihr C1 und C2.

**C4 Model — Übersicht**


|  | Level | Was zeigt es? | Heute |
| --- | --- | --- | --- |
| C1 | System Context | Euer System + wer damit interagiert (Nutzer, externe Systeme) | ✅ Ja — in dieser Übung |
| C2 | Container | Was läuft wo? Web App, API, DB, Mobile App — jeder Container = eigener Prozess | ✅ Ja — in dieser Übung |
| C3 | Component | Was ist innerhalb eines Containers? Module, Klassen, Services | Modul 5 — Coding Phase |
| C4 | Code | UML-Diagramme, Klassen-Details — meistens zu viel Detail | Optional |


Teil 1 · C1 System Context Diagram (15 Min)
Das grosse Bild: Euer System als schwarze Box — wer interagiert damit von aussen?

```
Erstelle ein C4 System Context Diagram für unser Projekt.
Projektname: [EUER PROJEKTNAME]
Beschreibung: [KURZE BESCHREIBUNG]
Zeige:
- Unser System (als Hauptelement in der Mitte)
- Alle Nutzertypen die damit interagieren
- Alle externen Systeme (E-Mail, Payment, Auth, APIs...)
- Wie sie interagieren (kurze Beschriftung der Pfeile)
Beschreibe das Diagram als Text mit klaren Boxes und Pfeilen.
Dann: Was haben wir vergessen?
```



**C1 — System Context: LearnFlow**

```
                        ┌─────────────────────────────────────────┐
                        │                                         │
     [Lara]             │              LearnFlow                  │          [LLM-Provider]
  Lernende/             │   Interne RAG-basierte Lernplattform    │◄────────► Cloud: Azure OpenAI
  Mitarbeiterin  ──────►│   für Fachdomänen-Wissen auf Basis      │          / Anthropic Claude
  stellt Fragen,        │   eines kuratierten Dokumenten-Korpus   │
  liest Antworten,      │                                         │◄────────► OnPrem: Ollama / vLLM
  gibt Feedback         └─────────────────────────────────────────┘          (datenschutzkritische
                                         ▲                                    Deployments)
                                         │
                        ┌────────────────┴────────────────┐
                        │                                 │
                   [Stefan]                          [Admin / IT]
              Bereichsverantwortlicher             Verwaltet Accounts
              lädt Dokumente hoch,                 per DB-Script,
              konfiguriert Schwellenwerte          überwacht System
              via Admin-UI,
              prüft Fragetrends + Feedback
```


**System-Name (Mitte):** LearnFlow — Interne RAG-basierte Lernplattform


**Nutzertypen (wer interagiert?):**

| Akteur | Rolle | Interaktion |
| --- | --- | --- |
| **Lara** (Lernende / neue Mitarbeiterin) | Hauptnutzerin | Stellt Fachfragen via Web-UI · liest quellenbelegte Antworten · gibt Feedback zu Antwortqualität · löst Quiz-Aufgaben |
| **Stefan** (Bereichsverantwortlicher / Fachbereich) | Korpus-Owner + Konfigurator | Lädt Dokumente hoch · konfiguriert Konfidenz-Schwellenwerte via Admin-UI · prüft Fragetrends und Feedback-Cluster · gibt Korpus frei |
| **Admin / IT** | Systemverwaltung | Legt Accounts per DB-Script an · überwacht Systemzustand · führt Deployments durch |


**Externe Systeme (welche Abhängigkeiten?):**

| System | Typ | Kommunikation | Notiz |
| --- | --- | --- | --- |
| **Azure OpenAI / Anthropic Claude** | LLM-Provider Cloud | HTTPS · REST | Generierung + Embeddings · DSGVO: Daten verlassen EU nicht (Azure EU-Region) |
| **Ollama / vLLM** | LLM-Provider OnPrem | HTTP lokal | Für datenschutzkritische Deployments ohne Cloud-Erlaubnis · schlechtere Antwortqualität als Cloud |


**Überraschungen — was hat AI gefunden das wir vergessen hatten?**

**Kein Dokumenten-Quellsystem eingebunden.** Die Dokumente im Korpus stammen irgendwoher — vermutlich aus SharePoint, Confluence oder einem Netzlaufwerk. Im C1 fehlt diese Quelle vollständig. Stefan lädt manuell hoch, aber das Dokument muss erst irgendwoher kommen. Post-MVP-Frage: direkte Integration in das bestehende Dokumentenmanagementsystem?

**Admin/IT ist kein expliziter Akteur in den User Stories.** Die Account-Verwaltung via DB-Script erfordert jemanden der das Script ausführt — aber dieser Akteur taucht in keiner User Story auf. Wer macht das operativ? Ist das Stefan, IT oder ein Entwickler?




Teil 2 · C2 Container Diagram (20 Min)
Jetzt zoomen wir rein: Was läuft technisch wo? Welche Technologien nutzt ihr?

```
Erstelle jetzt ein C4 Container Diagram für unser Projekt.
Basierend auf unseren Quality Attributes aus Übung 1:
[TOP 3 QAs EINFÜGEN]
Und unserer Systemübersicht aus C1:
[C1 ERGEBNIS EINFÜGEN]
Fragen:
1. Welche Container brauchen wir? (Web App, API, DB, Cache?)
2. Welche Technologien passen zu unserem Team und QAs?
3. Wie kommunizieren die Container miteinander?
4. Begründe jeden Container in einem Satz.
Unser Team: 2-3 Devs, 3 Monate, gemischter Background.
```



**C2 — Container Diagram: Unsere Technologie-Entscheidungen**

```
┌────────────────────────────────────── LearnFlow System ──────────────────────────────────────────────┐
│                                                                                                       │
│  ┌──────────────────┐   REST / SSE   ┌───────────────────────┐    SQL     ┌──────────────────────┐  │
│  │   React SPA      │ ◄────────────► │   FastAPI Backend     │ ◄────────► │  PostgreSQL          │  │
│  │                  │                │                       │            │  + pgvector          │  │
│  │  React + TS      │                │  Python · FastAPI     │            │                      │  │
│  │  Vite · Port 80  │                │  Auth-Modul (ADR-002) │            │  Dokumente · Chunks  │  │
│  │                  │                │  RAG-Pipeline+        │            │  Vektoren · Accounts │  │
│  │  Q&A · Feedback  │                │  Halluz.-Unterdrückung│            │  Config · Logs       │  │
│  │  Quiz · Admin-UI │                │  (ADR-001)            │            │  Port 5432           │  │
│  └──────────────────┘                │  Port 8000            │            └──────────────────────┘  │
│                                      └───────────┬───────────┘                      ▲               │
│                                                  │ Task-Queue                       │ SQL            │
│                                                  ▼                                  │               │
│                                      ┌───────────────────────┐                      │               │
│                                      │  Document Worker      │ ─────────────────────┘               │
│                                      │                       │                                       │
│                                      │  Python · asyncio     │                                       │
│                                      │  Chunking → Embedding │                                       │
│                                      │  → pgvector-Index     │                                       │
│                                      └───────────┬───────────┘                                       │
│                                                  │ LiteLLM (Library — kein eigener Container)        │
└──────────────────────────────────────────────────┼────────────────────────────────────────────────── ┘
                                                   │ HTTPS
                          ┌────────────────────────┼────────────────────────┐
                          │                        │                        │
                   [Azure OpenAI]         [Anthropic Claude]        [Ollama / vLLM]
                    Cloud · EU-Region       Cloud · EU-Region         OnPrem-Container
                    LLM + Embeddings        LLM + Embeddings          (nur OnPrem-Deployment)
```


| Container | Technologie | Aufgabe | Kommuniziert mit |
| --- | --- | --- | --- |
| **React SPA** | React · TypeScript · Vite | Q&A-UI für Lara (Fragen, Antworten, Feedback, Quiz) · Admin-UI für Stefan (Dokument-Upload, Schwellenwert-Config, Fragetrend-Analyse) | FastAPI Backend via REST (CRUD) · SSE (Streaming-Antworten, Token-by-Token) |
| **FastAPI Backend** | Python · FastAPI · LiteLLM (Library) | RAG-Pipeline mit dreistufiger Halluzinations-Unterdrückung (ADR-001) · JWT-Auth-Modul (ADR-002) · Admin-API für Threshold-Config · Dokument-Upload-Endpunkt (nimmt an, delegiert an Worker) | React SPA · PostgreSQL + pgvector · Document Worker · LLM-Provider via LiteLLM |
| **Document Worker** | Python · asyncio | Asynchrone Verarbeitung hochgeladener Dokumente: Chunking → Embedding via LiteLLM → Vektoren in pgvector schreiben → Index aufbauen. Upload-Response sofort (non-blocking), Verarbeitung im Hintergrund (≤ 5 Min. SLA) | PostgreSQL + pgvector · LLM-Provider via LiteLLM (Embeddings) |
| **PostgreSQL + pgvector** | PostgreSQL 16 · pgvector Extension | Einziger Datenspeicher: Dokument-Chunks + Vektoren (RAG) · User-Accounts + Rollen · Config-Tabelle (Schwellenwerte) · Feedback + Query-Logs · Stale-Markierungen | FastAPI Backend · Document Worker |
| **Ollama / vLLM** *(nur OnPrem)* | Ollama (Dev/ressourcenarm) · vLLM (Prod mit GPU) | LLM-Generierung + Embeddings lokal, ohne Cloud-Abhängigkeit. Nur in datenschutzkritischen Deployments aktiv; Cloud-Deployments nutzen Azure OpenAI / Claude direkt via HTTPS | FastAPI Backend · Document Worker (via LiteLLM) |


**Was überrascht uns an der AI-Empfehlung?**

**Kein Redis / Cache-Layer vorgeschlagen.** Angesichts des 10s @ p95 Performance-SLA hätte ein Cache für häufig gestellte Fragen nahegelegen. Die AI hat ihn weggelassen — zu Recht für MVP (< 30 Nutzer, kaum Wiederholungsfragen zu erwarten). Für Post-MVP bei mehr Last ist ein Query-Cache eine naheliegende Erweiterung.

**Kein API Gateway / Reverse Proxy als eigener Container.** Für Produktion wäre nginx vor dem FastAPI Backend üblich. Die AI hat das nicht modelliert — Docker Compose übernimmt das Routing im MVP. Für eine produktive Deployment-Variante muss das nachgezogen werden.

**LiteLLM als Library, nicht als Container.** LiteLLM kann auch als eigenständiger Proxy-Server betrieben werden (LiteLLM Proxy), was zentrale API-Key-Verwaltung und Rate-Limiting ermöglicht. Für MVP ist die Library-Variante einfacher — aber der Proxy-Modus ist eine sinnvolle Post-MVP-Option wenn mehrere Services LLM-Calls machen.


**Was ändern wir und warum?**

**Wir behalten die Vereinfachungen bewusst bei.** Kein Redis, kein API Gateway, kein Celery-Broker für den Document Worker — für < 30 Nutzer und 320–480 h Budget ist jeder zusätzliche Container operativer Overhead ohne messbaren Nutzen. Die Architektur ist so gebaut, dass diese Komponenten addiert werden können ohne Redesign (stateless Backend, klare Modul-Grenzen).

**Document Worker läuft im gleichen Docker-Compose-Stack wie das Backend**, nicht als isolierter Microservice. Das vereinfacht Deployment und lokale Entwicklung erheblich. Falls der Worker später skaliert werden muss, kann er extrahiert werden — das Interface (Aufgabe in Queue schreiben, Ergebnis in DB lesen) bleibt gleich.




Teil 3 · Kurze Vorstellung im Plenum (5 Min pro Team)
Jedes Team zeigt in 5 Minuten:
- C1: Wer interagiert mit eurem System?
- C2: Welche Container — und welche Technologie für die wichtigste Entscheidung?
- Euer ADR aus Übung 2: Was habt ihr entschieden und warum?
- Eine Überraschung: Was hat AI gefunden das ihr nicht erwartet hattet?


**Ausblick: Was kommt in Tag 2 und Modul 4?**
Heute habt ihr Quality Attributes, ein ADR und erste C4-Diagramme für euer Projekt. Das ist die Basis für: Tag 2 — System Design Patterns: Monolith vs Microservices, API-First, Event-Driven Modul 4 — Planung: Eure Architektur wird zum Sprint-Plan Modul 5 — Coding: Claude Code arbeitet mit eurer C2/C3-Struktur Je präziser eure Architektur heute — desto klarer der Weg durch den Rest des Kurses.



CAS ADAI 2026 · BFH Biel · Modul 3 Tag 1 · Ilja Rasin
