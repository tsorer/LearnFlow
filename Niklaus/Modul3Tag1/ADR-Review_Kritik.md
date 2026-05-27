# ADR-Review — Kritische Analyse ADR-001 bis ADR-005

*Datum: 2026-05-27 · Reviewer: Claude (KI-gestützt)*

---

## 1. Was haben wir nicht bedacht?

### ADR-001 / ADR-002 — Widerspruch: Celery + Redis vs. Monolith
ADR-001 verkauft "ein Deployment-Artefakt" als zentralen Vorteil. ADR-002 nennt als Mitigation für persistente Jobs "Celery + Redis". Das ist kein Detail — das ist ein Redis-Message-Broker + ein separater Celery-Worker-Container. Das sind zwei zusätzliche Services. Der "modulare Monolith"-Vorteil gilt dann nur noch für den Anwendungscode, nicht für das Deployment. Das ist ein interner Widerspruch zwischen zwei ADRs, der nirgends explizit entschieden wurde.

### ADR-003 — `bytea` vs. Large Objects: noch nicht entschieden
Das ADR sagt "bytea" und nennt als Mitigation "lo evaluieren". Das ist keine Entscheidung, das ist eine offene Frage als Entscheidung verkleidet. `bytea` lädt das gesamte Binary in den Arbeitsspeicher — ein 100 MB PDF kostet bei einem SELECT sofort 100 MB RAM auf dem Datenbankserver. Bei fünf gleichzeitigen Downloads sind das 500 MB. PostgreSQL Large Objects (`pg_largeobject`) sind für grosse Binaries explizit gebaut, haben aber eine andere API. Das muss entschieden werden, bevor das Schema erstellt wird.

### ADR-003 — Azure-Referenz in negativer Konsequenz
Zeile "Migration zu Azure Blob Storage" als Post-MVP-Pfad. Azure wurde aber bewusst verlassen (ADR-004). Sollte "S3-kompatibler Object Storage (z. B. MinIO)" heissen.

### ADR-004 — Keine Kostenschätzung
"Für < 30 Pilotnutzer überschaubar" ist nicht messbar. Eine grobe Kalkulation fehlt: ~30 Fragen/Tag × 30 Nutzer × ~2 000 Token/Anfrage = ~1.8M Token/Tag. Bei gpt-4o-mini (~$0.15/1M Input, $0.60/1M Output) wären das ca. $1–3/Tag — vernachlässigbar. Das hinzuzuschreiben würde die Entscheidung stärken statt schwächen.

### ADR-004 — OpenAI Data Opt-Out nicht erwähnt
OpenAI verwendet API-Daten standardmässig nicht für Training (API ≠ ChatGPT WebUI). Das ist ein wichtiges Datenschutz-Argument das im ADR fehlt und die DSGVO-Diskussion entschärfen würde.

### ADR-005 — Chunking-Strategie fehlt komplett
Das Embedding-Modell ist eine Entscheidung. Die Chunking-Strategie ist mindestens so wichtig für die RAG-Qualität — und fehlt als ADR vollständig. Fixed-size vs. Semantic Chunking, Chunk-Grösse (512 vs. 1024 Token), Overlap (0 vs. 20 %) — das beeinflusst direkt die Retrieval-Präzision und damit die Reliability-NFA (Halluzinationsrate = 0 %). **→ ADR-006 fehlt.**

### ADR-004 + ADR-005 — Rate Limiting bei Bulk-Upload nicht adressiert
Stefan lädt 30 Dokumente hoch → tausende Embedding-API-Calls in kurzer Zeit → OpenAI Rate Limit (tokens-per-minute) kann ausgelöst werden. Fehlt als negative Konsequenz in beiden ADRs.

---

## 2. Welche Alternativen fehlen?

| ADR | Fehlende Alternative | Begründung |
|---|---|---|
| ADR-001 | — | Vollständig |
| ADR-002 | **LangChain vs. kein Framework** | LangChain wird als gegeben vorausgesetzt, nie als Entscheidung behandelt. Die Alternative — direkte OpenAI-SDK-Calls + eigene RAG-Implementierung — fehlt als verworfene Option. LangChain hat bekannte Breaking-API-Changes; für 360 h könnte eine dünnere Implementierung robuster sein. |
| ADR-003 | — | Vollständig für den Scope |
| ADR-004 | **Groq** | Groq bietet llama3-basierte Inferenz mit sehr tiefer Latenz. Für einen Pilot mit wenig Nutzern und Kostenoptimierung relevant. |
| ADR-005 | **Voyage AI (`voyage-multilingual-2`)** | Anthropic-affiliiert, explizit für mehrsprachige Dokumente trainiert — relevant für deutsche Fachtexte. Fehlt als Alternative. |

---

## 3. Sind die Konsequenzen vollständig und realistisch?

### ADR-002 — Celery + Redis ist eine negative Konsequenz, keine Mitigation
"Celery + Redis als Mitigation" ist eine Beschönigung. Es ist eine negative Konsequenz: *"Der 5-Minuten-SLA für Dokument-Verarbeitung erfordert einen persistenten Job Queue (Redis + Celery Worker) — das sind zwei zusätzliche Deployment-Artefakte entgegen ADR-001."* Das sollte so stehen.

### ADR-004 — Datenschutz-Mitigation zu vereinfacht
"Auf Ollama umstellen — eine Konfigurationszeile" stimmt für den LLM. Aber ein Datenschutz-Switch bedeutet auch: Embedding-Modell wechseln (ADR-005) + alle Dokumente re-indexieren. Das ist keine Konfigurationszeile für das Gesamtsystem. Die Interdependenz mit ADR-005 fehlt.

### ADR-005 — Dev/Prod-Inkompatiblität hat praktische Debugging-Konsequenz
1536 Dim (Prod) vs. 1024 Dim (Dev) bedeutet: ein Retrieval-Problem das in Produktion auftritt, kann in der lokalen Entwicklungsumgebung nicht reproduziert werden. Das ist mehr als "separate Installationen mit separaten Daten" — das ist eine eingeschränkte Debuggability.

### ADR-003 — VACUUM/Autovacuum fehlt
Die `embeddings`-Tabelle wird bei jedem Re-Upload gelöscht und neu befüllt. PostgreSQL's Autovacuum kann bei vielen Delete/Insert-Zyklen auf grossen Tabellen table bloat verursachen. Für den Pilot mit < 500 Dokumenten kein sofortiges Problem, aber fehlt als bekannte Limitation.

---

## 4. Grösstes Risiko

### Risiko 1 (kritisch): Kein ADR für Chunking & Retrieval-Strategie
Die gesamte Reliability-NFA (Halluzinationsrate = 0 %, Out-of-Corpus ≥ 90 % "Weiss ich nicht") hängt nicht primär am LLM-Provider oder Embedding-Modell — sie hängt an der RAG-Pipeline-Qualität: Chunk-Grösse, Overlap, Retrieval-Strategie (Dense vs. Hybrid Search), Re-Ranking. Diese Entscheidungen sind nirgends dokumentiert, obwohl sie im Tech Spike in Woche 1 getroffen werden müssen. Und sie sind teuer zu revidieren, weil ein Chunking-Wechsel immer eine vollständige Re-Indexierung bedeutet.

**→ ADR-006 für Chunking & Retrieval-Strategie fehlt.**

### Risiko 2 (signifikant): Celery + Redis als implizite Architektur-Entscheidung
Der Widerspruch zwischen ADR-001 (ein Deployment-Artefakt) und ADR-002 (Celery + Redis als Mitigation) ist nie explizit entschieden. Optionen:

- **Option A:** Akzeptieren dass der Job Queue ein separater Service ist → ADR-001 entsprechend anpassen.
- **Option B:** Postgres-nativer Job Queue (`pgqueuer` oder `pg-boss`) — kein Redis, kein Celery, PostgreSQL ist bereits vorhanden → Monolith bleibt echter.

---

## Zusammenfassung

| ADR | Kritischste Lücke | Priorität |
|---|---|---|
| ADR-001 | Celery + Redis aus ADR-002 widerspricht "ein Deployment-Artefakt" | Hoch |
| ADR-002 | LangChain als Entscheidung fehlt; Celery+Redis ist negative Konsequenz, keine Mitigation | Hoch |
| ADR-003 | `bytea` vs. Large Objects ungelöst; Azure-Referenz im Post-MVP-Pfad | Mittel |
| ADR-004 | Kostenschätzung fehlt; OpenAI Data Opt-Out nicht erwähnt; Rate Limiting fehlt | Mittel |
| ADR-005 | Chunking-Strategie fehlt → ADR-006 fehlt | Kritisch |

## Empfohlene nächste Schritte

1. **ADR-006 schreiben** — Chunking & Retrieval-Strategie (vor Tech Spike Woche 1)
2. **Celery+Redis-Widerspruch entscheiden** — Option A (akzeptieren + ADR-001 anpassen) oder Option B (pgqueuer statt Redis)
3. **ADR-003 `bytea` vs. `lo` entscheiden** — bevor das Datenbankschema erstellt wird
4. **ADR-004** — Kostenschätzung und OpenAI Data Opt-Out ergänzen

---

*Quellen: ADR-001 bis ADR-005 · LearnFlow_Requirements_v1.md · BFH CAS ADAI 2026*
