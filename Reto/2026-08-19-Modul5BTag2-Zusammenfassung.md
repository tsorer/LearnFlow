# Modul 5B / Tag 2 (ADAI) — Zusammenfassung

**Datum:** 2026-08-19 · **Kurs:** CAS Application Development with AI · **Details:** [Reto/Modul5BTag2/NOTES.md](Modul5BTag2/NOTES.md)

## Worum ging es?

Kurs-Lab zum Claude Agent SDK: vom einzelnen Agent zum kleinen "System" aus drei Bausteinen —
diesmal mit echtem Bezug zu unserem Semesterprojekt **LearnFlow** statt Spielzeug-Beispielen.

- **Hauptagent** = bekommt den Prompt direkt, steuert die Aufgabe.
- **Subagent** = vom Hauptagent per Agent-Tool aufgerufener Mini-Agent mit eigener Rolle, eigenem
  Prompt, eigenen Tools und eigenem Modell — löst einen Teilschritt und liefert das Ergebnis zurück.

Gebaut (in [Reto/Modul5BTag2/](Modul5BTag2/)):

1. **Subagent** `api-kritiker` — prüft, ob `openapi.yaml` und der FastAPI-Router zusammenpassen
   (ADR-010, API-First).
2. **Mini-Orchestrator** (Planner → Generator → Evaluator) — schreibt und prüft sich selbst eine
   kleine Upload-Validierungsfunktion nach ADR-003 (max. 10 MB, PDF/DOCX/MD).
3. **Guardrail** (`can_use_tool`) — loggt jeden Tool-Aufruf und blockiert einen Schreibversuch in
   eine generierte LearnFlow-Datei (`schema.d.ts`, laut CLAUDE.md tabu).

## Wichtigste Erkenntnisse

- **Delegation funktioniert zuverlässig ohne Namensnennung.** Der `api-kritiker`-Subagent hat sowohl
  mit als auch ohne explizite Namensnennung im Prompt gewonnen — kein Built-in-Skill hat übernommen.
- **Echte Bugs gefunden, nicht nur Übungs-Output.** Der Subagent hat zweimal denselben realen
  ADR-010-Verstoss in `documents.py` entdeckt: `status` ist als `str` statt als striktes Enum
  typisiert.
- **Nichtdeterminismus ist real, nicht nur Theorie.** Der P→G→E-Orchestrator lief mit identischem
  Prompt zweimal: Lauf 1 brach nach `max_turns` ab (Generator verhedderte sich in einer
  Berechtigungs-Anfrage, weil Prompt "setze um" sagte, aber keine Schreibrechte da waren — genau die
  im Lab beschriebene "Konsistenz-Falle"), Lauf 2 kam sauber mit PASS in Runde 1 durch.
- **Der Guardrail hat gehalten.** Der Write-Versuch auf `schema.d.ts` wurde blockiert; der Agent hat
  nicht versucht, das zu umgehen, sondern die CLAUDE.md-Regel korrekt zitiert und einen legitimen
  Alternativweg vorgeschlagen.
- **SDK-Versions-Stolpersteine (nicht im Lab-Dokument vorhergesehen):** `can_use_tool` funktioniert
  in der installierten SDK-Version nur mit einer durchgehend offenen Verbindung
  (`ClaudeSDKClient`, nicht die einmalige `query()`-Funktion). Ausserdem "shadowed" ein blosser
  Tool-Name in `allowed_tools` den Guardrail komplett (er wird dann nie aufgerufen) — Fix: kein
  `allowed_tools`, sondern `tools=[...]` als harte Tool-Begrenzung.
- **Setup-Details für dieses Kurs-Repo:** Scripte laufen in der conda-Umgebung `adai`
  (`conda activate adai`), Abrechnung über das Claude-Abo (`CLAUDE_CODE_OAUTH_TOKEN`), nie über
  `ANTHROPIC_API_KEY`.

## Wo liegt was

- Scripte + rohe Terminal-Outputs + Präsentations-Notizen: [Reto/Modul5BTag2/](Modul5BTag2/)
- Ausgefülltes Lab-Dokument (grün, mit Präsentations-Gliederung):
  `2026_08_19_ADAI_Modul5B_Tag2_Lab_ausgefüllt.docx` (im Unterrichtsordner, nicht im Repo)
