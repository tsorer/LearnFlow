Du bist ein erfahrener Software-Architekt. Überarbeite unsere zwei zentralen ADRs basierend auf den Erkenntnissen aus dem AI-Review (L1).

**Kontext:**
- Projekt: LearnFlow — interne RAG-Lernplattform, MVP bis 30. September 2026, 3 Devs, ~360 h
- Review-Erkenntnisse aus L1: [ERKENNTNISSE AUS L1 EINFÜGEN]
- Bestehende ADRs: Docs/04_ADR-001_Architekturstil.md, Docs/04_ADR-002_Backend-Frontend-Stack.md

**Finalisiere ADR-001 (Architekturstil — Modularer Monolith):**

Erstelle eine bereinigte, finale Version mit:
- Titel
- Status: Accepted
- Kontext (1–2 Sätze: warum war diese Entscheidung nötig?)
- Entscheidung (1 Satz: was haben wir entschieden?)
- Begründung (die 3 stärksten Argumente — konkret für LearnFlow)
- Konsequenzen (je 2–3 positive und negative)
- Was müssen wir tun damit diese Wahl wirklich funktioniert?

**Finalisiere ADR-002 (Backend/Frontend-Stack — FastAPI + React):**

Gleiche Struktur. Berücksichtige besonders:
- SSE-Streaming als Kernanforderung
- KI-gestützte Implementierung mit Claude Code als Entwicklungsmodell
- Python-Ökosystem für RAG (LangChain, LiteLLM, sentence-transformers)

Halte jeden ADR auf max. 1 Seite — klar und repo-tauglich.
