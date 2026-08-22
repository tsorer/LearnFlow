# Modul 5B Tag 2 — Notizen für die 3-Min-Präsentation

Ausfüllen während/nach dem Ausführen der drei Skripte.

## L1 — Subagent (`subagent_api_kritiker.py`) — 45 Sek

- Rolle: **api-kritiker** (vergleicht `openapi.yaml` mit `documents.py`, ADR-010)
- Lauf MIT Rollennamen: Agent-Tool-Call im Stream gesehen? ✅ Ja (`TOOL: Agent`, `subagent_type: api-kritiker`)
- Fund (Bonus, real): `DocumentResponse.status` ist `str` statt `DocumentStatus`-Enum — ADR-010-Abweichung
- Lauf OHNE Rollennamen (`--ohne-namen`): wer gewinnt — eigener Subagent oder Built-in-Skill? ✅ wieder api-kritiker, kein Skill übernimmt
- Kosten (`total_cost_usd`): $0.3446 · 2 Turns (Lauf 1) / $0.2448 · 2 Turns (Lauf 2) = $0.5894 total

## L2 — P→G→E (`pge_upload_validierung.py`) — 1 Min

- Lauf 1: **kein PASS** — FAIL in Runde 2, `max_turns` erreicht (Konsistenz-Falle: Generator-Prompt
  „setze um" + `tools=[]` → Agent fragt nach Schreibrechten statt nur Code auszugeben, verbrennt
  Turns). `try/except` hat sauber abgefangen, kein Absturz. Evaluator-Runde 1 hat echten Bug im
  generierten Code gefunden: `Path(".pdf").suffix` liefert `""` (Dotfile-Semantik).
- Lauf 2: **PASS in Runde 1** (Generator wollte wieder Schreibzugriff, lieferte den Code aber
  trotzdem direkt als Text mit → diesmal reichte es dem Evaluator)
- Kosten: im Skript nicht einzeln ausgegeben (wie Vorlage `test_pge.py`); Budget-Caps pro Aufruf:
  Planner ≤$0.20, Generator ≤$0.30, Evaluator ≤$0.20 — Lauf 1 brauchte mehr Aufrufe (bis Abbruch in
  Runde 2), Lauf 2 nur je 1× Generator+Evaluator (PASS in Runde 1) → Lauf 2 günstiger
- **Unterschied zwischen den Läufen (Kernaussage für Präsentation):** identischer Prompt, komplett
  unterschiedliches Ergebnis — Lauf 1 bricht nach `max_turns` ab (Konsistenz-Falle), Lauf 2 PASS in
  Runde 1. Klassischer Nichtdeterminismus-Beweis aus dem Lab.

## L3 — Guardrail (`guardrail_api_kritiker.py`) — 45 Sek

- Blockierter Aufruf (Write auf schema.d.ts): Deny-Meldung gesehen? ✅ Ja
- Reaktion des Agents auf das Deny: **Alternativvorschlag** — hat die Blockade akzeptiert, CLAUDE.md-
  Tripwire korrekt zitiert (schema.d.ts wird generiert, manuelle Edits gehen bei `make generate-api`
  verloren) und einen legitimen manuellen Alternativweg vorgeschlagen (`echo >> schema.d.ts` selbst
  ausführen) statt es zu erzwingen
- Anzahl Aufrufe laut `audit_log`: **6** (4× Read, 1× Grep, 1× Write — der geblockte)
- Bonus-Fund: `GET /documents` nutzt `response_model=list[DocumentResponse]` statt `$ref: DocumentList`
  aus der Spec — funktional gleich, aber ADR-010-Abweichung
- Kosten: $0.3426 · 4 Turns
- Stolperstein unterwegs (SDK-Version-Drift, nicht im Lab-Dokument vorhergesehen): `can_use_tool`
  braucht in `claude-agent-sdk` 0.2.140 eine offene bidirektionale Verbindung — `query()` mit
  Einweg-Prompt bricht mit „Stream closed" ab, `ClaudeSDKClient` (hält Verbindung offen) behebt es.
  Ausserdem: ein bloßer Tool-Name in `allowed_tools` „shadowed" `can_use_tool` (wird nie aufgerufen) —
  daher `allowed_tools` weggelassen und stattdessen `tools=[...]` zur harten Tool-Begrenzung genutzt.

## L4 — Kurzpräsentation (3 Min, 4 Teile)

**1) Subagent-Rolle — 45 Sek**
*Begriffe: Hauptagent = der Agent, der deinen Prompt direkt bekommt und die Aufgabe steuert.
Subagent = ein vom Hauptagent per Agent-Tool aufgerufener Mini-Agent mit eigener Rolle, eigenem
Prompt, eigenen Tools und eigenem Modell — bearbeitet einen Teilschritt und liefert das Ergebnis
zurück an den Hauptagenten.*
*Kontext: L1 — ein spezialisierter Subagent für eine Rolle aus LearnFlow; Test, ob der Haupt-Agent
automatisch an ihn delegiert.*
- Rolle: api-kritiker — prüft ob `openapi.yaml` und Router-Code (`documents.py`) zusammenpassen
  (ADR-010, API-First)
- Delegation gewonnen: MIT und OHNE Rollenname — kein Built-in-Skill hat übernommen
- Bonus: echter kleiner Spec-Bug gefunden (`status`-Feld ohne Enum)
- Kosten: $0.59 (2 Läufe)

**2) P→G→E — 1 Min**
*Kontext: L2 — drei Rollen (Planner/Generator/Evaluator) schreiben & prüfen selbst eine kleine
Funktion; hier: Upload-Validierung nach ADR-003 (max. 10 MB, PDF/DOCX/MD).*
- Lauf 1: FAIL (`max_turns`) — Generator verheddert sich in Berechtigungs-Anfrage (Konsistenz-Falle
  aus dem Lab, live erlebt)
- Lauf 2: PASS in Runde 1 — exakt gleicher Prompt, anderes Ergebnis
- Zeigt: Nichtdeterminismus ist real — dafür braucht's Evaluator + Runden-Limit

**3) Guardrail-Demo — 45 Sek**
*Kontext: L3 — `can_use_tool` loggt jeden Tool-Aufruf und blockiert eine gefährliche Aktion; hier:
Schreibversuch in eine generierte LearnFlow-Datei (`schema.d.ts`), laut CLAUDE.md tabu.*
- Blockade ausgelöst: Write auf `schema.d.ts` → Deny im Stream sichtbar
- Agent-Reaktion: kein Umgehungsversuch — zitiert die Projektregel korrekt, schlägt legitime
  Alternative vor
- `audit_log`: 6 Aufrufe protokolliert (4× Read, 1× Grep, 1× Write/geblockt)

**4) Kosten-Bilanz — 30 Sek**
*Kontext: Was kostet der einfache Subagent-Ansatz gegenüber dem Mehr-Rollen-Orchestrator?*
- Subagent (L1, 2 Läufe): $0.59 · Guardrail-Lauf (L3, auch Subagent-basiert): $0.34
- P→G→E (L2): nicht einzeln geloggt, aber mehr Rollen/Aufrufe je nach Rundenzahl — tendenziell teurer
- Fazit: Subagent = günstig & vorhersagbar für klar abgegrenzte Routineaufgaben; Orchestrator =
  teurer, aber selbstkorrigierend bei generativen Aufgaben
