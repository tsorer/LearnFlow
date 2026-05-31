# ADR-Review — Kritische Analyse ADR-001 bis ADR-009

*Erst-Review: 2026-05-27 · Update: 2026-05-31 · Reviewer: Claude (KI-gestützt)*

> **Update 2026-05-31:** Dieses Dokument wurde nach Überarbeitung der ADR-Serie aktualisiert. Erledigte Punkte sind als **✅ erledigt** markiert, Restlücken als **offen**. Neu hinzugekommen sind ADR-007 (Chunking/Retrieval), ADR-008 (Konfidenzpipeline) und ADR-009 (Eval-Strategie) — die im Erst-Review als kritischste Lücken benannten Themen.

---

## 1. Was haben wir nicht bedacht? — Status der Erst-Review-Punkte

### ✅ ADR-001 / ADR-002 — Widerspruch Celery + Redis vs. Monolith
**Erledigt (2026-05-27):** Aufgelöst durch **ADR-006 (pgqueuer)** — PostgreSQL-nativer Job-Queue, kein Redis, kein Celery. Der „ein Deployment-Artefakt"-Vorteil aus ADR-001 bleibt erhalten.

### offen — ADR-003 — `bytea` vs. Large Object
**Teilweise adressiert:** Die `bytea`-Entscheidung steht weiterhin, die Nachteile (WAL-Bloat, RAM bei SELECT grosser Binaries) sind nun explizit als negative Konsequenz dokumentiert, und **MinIO/Object Storage** ist als ehrliche Alternative + erste Migrationsoption ergänzt. **Noch offen:** die definitive `bytea`-vs-`lo`-Entscheidung vor Schema-Erstellung. Für die Pilotgrösse (< 500 Dokumente) vertretbar zurückgestellt.

### ✅ ADR-003 — Azure-Referenz in negativer Konsequenz
**Erledigt:** „Migration zu Azure Blob Storage" → **S3-kompatibler Object Storage (MinIO)** korrigiert. (Hinweis: LearnFlow nutzt für den LLM-Endpunkt nun wieder Azure OpenAI EU — die Object-Storage-Wahl bleibt davon unberührt MinIO/S3.)

### offen — ADR-004 — Keine Kostenschätzung
**Noch offen:** Die grobe Token-Kalkulation (~1.8M Token/Tag → ca. $1–3/Tag) fehlt weiterhin im ADR. Würde die Entscheidung stärken. Empfehlung: als positive/neutrale Konsequenz ergänzen. (Hinweis: Abrechnung läuft nun über das Azure-Enterprise-Agreement, vgl. ADR-004.)

### ✅ ADR-004 — Datenschutz: US-Server / Data Opt-Out
**Erledigt — grundlegender als vorgeschlagen:** Statt nur den OpenAI-Data-Opt-Out zu erwähnen, wurde der Produktiv-Default auf **Azure OpenAI EU** umgestellt (EU-Datenresidenz). Damit ist die DSGVO-Diskussion am Kern gelöst, nicht nur entschärft. OpenAI Direct bleibt Dev-/Test-Pfad ohne Produktivdaten, Ollama als OnPrem-Option.

### ✅ ADR-005 — Chunking-Strategie fehlt komplett
**Erledigt:** Nun als eigenständiges **ADR-007 (Chunking & Retrieval)** dokumentiert — struktur-bewusstes Chunking, Hybrid-Retrieval (Dense + Sparse/RRF), Schwellenwert-Gate.

### offen — ADR-004 + ADR-005 — Rate Limiting bei Bulk-Upload
**Teilweise adressiert:** ADR-004 verweist auf „Azure-Quotas/Rate-Limiting vor Go-Live konfigurieren", und ADR-006 benennt das Embedding-Rate-Limit als realen Throughput-Engpass. **Noch offen:** eine explizite Mitigation (Drosselung/Batching/Retry mit Backoff) für den Fall „Stefan lädt 30 Dokumente gleichzeitig hoch" — gehört als negative Konsequenz konkretisiert.

---

## 2. Welche Alternativen fehlen? — Status

| ADR | Erst-Review: fehlende Alternative | Status |
|---|---|---|
| ADR-001 | — | Vollständig |
| ADR-002 | **LangChain vs. kein Framework** | **offen** — LangChain/LiteLLM werden vorausgesetzt, nie als Entscheidung behandelt. Die Alternative „dünne Eigenimplementierung statt LangChain" fehlt weiterhin. Kandidat für ein eigenes ADR oder einen Zusatz in ADR-002. *(Frontend-Alternativen Vue/Svelte/HTMX wurden ergänzt.)* |
| ADR-003 | MinIO/Object Storage | **✅ ergänzt** als Alternative |
| ADR-004 | **Groq** | **offen** — als Niedriglatenz-Alternative weiterhin nicht erwähnt. Geringe Priorität: LiteLLM erlaubt späteren Wechsel, und Datenresidenz spräche ohnehin gegen einen US-Anbieter ohne EU-Garantie. |
| ADR-005 | **Voyage AI / multilinguale Modelle** | **teilweise** — `text-embedding-3-large` als Alternative ergänzt und Produktionsmodell als Spike-Eval markiert; ein dediziert multilinguales Modell (Voyage/E5/Jina) als Eval-Kandidat genannt, aber nicht als eigene Tabellenzeile. |

---

## 3. Sind die Konsequenzen vollständig und realistisch? — Status

### ✅ ADR-002 — Celery + Redis als Konsequenz statt Mitigation
**Gegenstandslos:** Mit ADR-006 (pgqueuer) entfällt Celery + Redis vollständig; der Punkt ist durch die Entscheidung überholt.

### ✅ ADR-004 — Datenschutz-Mitigation zu vereinfacht
**Erledigt:** Die Interdependenz ist nun dokumentiert — ein OnPrem-/Datenschutz-Switch betrifft LLM (ADR-004) *und* Embedding-Modell (ADR-005, inkl. vollständiger Re-Indexierung). ADR-005 nennt die Re-Indexierungskosten explizit.

### offen — ADR-005 — Dev/Prod-Inkompatibilität (1536 vs. 1024)
**Anerkannt, nicht beseitigt:** Die eingeschränkte Debuggability (Prod-Retrieval-Probleme lokal nicht reproduzierbar) ist als bewusster Trade-off dokumentiert; ADR-005 weist zudem darauf hin, dass Matryoshka-Reduktion eine Vereinheitlichung ermöglichen *könnte*. Bleibt eine akzeptierte Limitation.

### offen — ADR-003 — VACUUM/Autovacuum bei Re-Index-Zyklen
**Noch offen:** Table-Bloat durch Delete/Insert-Zyklen auf der `embeddings`-Tabelle ist weiterhin nicht als bekannte Limitation vermerkt. Für < 500 Dokumente unkritisch, sollte aber als negative Konsequenz ergänzt werden.

---

## 4. Bewertung der neuen ADRs (007–009)

### ADR-007 — Chunking & Retrieval
Schliesst die im Erst-Review als **kritisch** markierte Lücke. Stark: Hybrid-Retrieval (Dense + deutsche Volltextsuche, RRF) adressiert deutsche Fachbegriffe/Akronyme; das **Schwellenwert-Gate** ist der deterministische, billige Kernschutz gegen Halluzinationen. Offene Punkte sind ehrlich benannt (Parameter sind Spike-Hypothesen; Re-Ranking bewusst out-of-MVP; Abhängigkeit zur Eval-Strategie).

### ADR-008 — Konfidenz- & Unterdrückungspipeline
Spezifiziert die zuvor nur im C4 vorausgesetzte „Konfidenz-Unterdrückungspipeline" als mehrstufige, **fail-closed** Defense-in-Depth. Stark: deterministische Kern-Gates (provider-portabel, keine Logprob-Abhängigkeit), Self-Check nur für Grenzfälle (Kostenkontrolle), US-02 direkt erfüllt. Restrisiko (Citation-Coverage misst Form, nicht Korrektheit) ist benannt.

### ADR-009 — Eval-Strategie
Macht die Reliability-NFA überhaupt erst **verifizierbar** und kalibrierbar. Stark: Gold-Dataset mit In-/Out-of-Corpus/Adversarial-Mix, CI-Regressionsgate (Build bricht bei Halluzination > 0 %), statistische Ehrlichkeit (0 % nur demonstrierbar, nicht beweisbar → Produktions-Monitoring ergänzt). Grösster Aufwandstreiber (Fachbereichs-Zeit fürs Dataset) ist offen benannt.

---

## 5. Grösstes Risiko — aktualisiert

### ✅ Risiko 1 (war kritisch): Kein ADR für Chunking & Retrieval
**Erledigt:** ADR-007 (Chunking/Retrieval) + ADR-008 (Konfidenz) + ADR-009 (Eval) decken die RAG-Qualitäts- und Reliability-Kette jetzt ab.

### ✅ Risiko 2 (war signifikant): Celery + Redis als implizite Architektur-Entscheidung
**Erledigt 2026-05-27:** pgqueuer (ADR-006).

### offen — Risiko 3 (neu, signifikant): Datenmodell & API-Kontrakt fehlen
ADR-002 begründet die Architektur mit „OpenAPI-Spec als saubere Grenze für parallele Arbeit" — genau diese Spec (Endpunkte, Request/Response-Schemas) und das **Tabellen-Schema** existieren aber noch nicht. Beides ist vor dem ersten Code zwingend (kein klassischer ADR, sondern ein Spike-0-Deliverable).

### offen — Risiko 4 (neu, mittel): NFA-Verifikation hängt am Gold-Dataset
ADR-009 ist nur so gut wie das fachlich abgenommene Gold-Dataset. Ohne Stefans Zeitbudget dafür bleibt die Reliability-NFA unbelegt — terminkritisch für Spike Woche 1.

---

## 6. Noch von keinem ADR abgedeckt (Cross-Cutting)

- **Auth/RBAC konkret:** Rollenmodell, Account-Provisionierung, Endpunkt-Autorisierungsmatrix (JWT/bcrypt ist entschieden, Details nicht).
- **Quiz-Generierung (US-07/08):** Generierung, Freigabe-Workflow, Speicherung — kein ADR.
- **Secret-Management:** API-Keys/DB-Credentials (in ADR-001 als Folgeentscheid markiert).
- **Observability/Logging:** im C1 als „vergessen" notiert, noch keine Entscheidung.
- **LangChain als Entscheidung** (siehe Abschnitt 2).

---

## Zusammenfassung — Stand 2026-05-31

| ADR | Kritischste Lücke (Erst-Review) | Status |
|---|---|---|
| ADR-001 | Celery+Redis-Widerspruch | ✅ pgqueuer (ADR-006) |
| ADR-002 | LangChain als Entscheidung; Frontend-Begründung schwach | Frontend ✅ überarbeitet · LangChain **offen** |
| ADR-003 | `bytea` vs. `lo`; Azure-Referenz | Azure-Ref ✅ · `bytea`/`lo` **offen** · MinIO ✅ ergänzt |
| ADR-004 | US-Datenhaltung; Kostenschätzung; Rate Limiting | Datenhaltung ✅ (Azure EU) · Kosten/Rate-Limit **offen** |
| ADR-005 | Chunking fehlt; Embedding-Sprachfit | Chunking ✅ (ADR-007) · `-large`/Spike-Eval ✅ ergänzt |
| ADR-006 | — | ✅ Accepted, Alternativen erweitert |
| ADR-007 | *(neu)* | ✅ erstellt — Chunking/Retrieval |
| ADR-008 | *(neu)* | ✅ erstellt — Konfidenzpipeline |
| ADR-009 | *(neu)* | ✅ erstellt — Eval-Strategie |

## Offene nächste Schritte

1. **Gold-Dataset mit dem Fachbereich aufbauen** (ADR-009) — terminkritisch vor Spike-Kalibrierung.
2. **Datenmodell + OpenAPI-Kontrakt** spezifizieren — vor dem ersten Code (Spike-0-Deliverable).
3. **ADR-003 `bytea` vs. `lo` entscheiden** — vor Schema-Erstellung.
4. **ADR-004** — Kostenschätzung ergänzen; Bulk-Upload-Rate-Limiting als Konsequenz/Mitigation konkretisieren.
5. **ADR-003** — Autovacuum/Table-Bloat als bekannte Limitation ergänzen.
6. **LangChain-Entscheidung** dokumentieren (eigenes ADR oder Zusatz in ADR-002).
7. Cross-Cutting-Themen (Auth-Detail, Quiz, Secrets, Observability) als ADRs/Spike-Tasks einplanen.

---

*Quellen: 04_ADR-001 bis 04_ADR-009 · 02_Requirements.md · 03_QualityAttributes.md · 05_C4-C1/C2 · BFH CAS ADAI 2026*
