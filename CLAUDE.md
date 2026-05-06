# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

**LearnFlow** is a course project for *CAS Application Development with AI 2026* at BFH Biel. It is a RAG-based internal Q&A platform that lets new employees (developers, requirements engineers, testers) ask questions about a company's domain knowledge and get **source-cited** answers from a curated, per-domain corpus. The reference domain in the pitch is *Sozialdienste* (social-services software).

The repo is at the **start of Sprint 0** (tech spike). There is currently no application code — only kickoff artefacts under `Artefakten/`. The full background (problem statement, personas, user stories, risks, canvas, plan) lives in the prework documents and should be consulted before making non-trivial decisions:

- `Artefakten/Modul1Tag2/LearnFlow_Plan_15Wochen.md` — the binding 15-week / 360 h plan and scope
- `Artefakten/Modul1Tag2/LearnFlow_Kickoff_Doku.docx` — structured kickoff documentation
- `Artefakten/Modul1Tag2/LearnFlow_Chatverlauf.md` — the reasoning trail behind the decisions (read this before re-litigating any decision)
- `Artefakten/Modul1Tag2/LearnFlow_Pitch.pptx` — 5-minute pitch deck

## Hard constraints

These are not preferences — the project plan depends on them:

- **Total budget: 360 person-hours** across 3 people × 15 weeks × 8 h. No headroom. Every "small wish" costs another story its slot.
- **Deadline: 30 September 2026** (presentation).
- **MVP scope is exactly four stories.** Anything else is concept-only documentation, not code:
  - **Story 1** — Q&A with cited sources
  - **Story 2 (minimal)** — Corpus ingestion via CLI/script (no admin UI)
  - **Story 3** — Feedback (👍/👎 + categories)
  - **Story 4** — Uncertainty / "Weiß ich nicht" with confidence threshold + self-check
- **Explicitly out of scope (concept docs only, do not implement):** stale-content detection (5), quiz (6a/6b), knowledge-gap dashboard (7), real SSO auth (8 — use a hardcoded demo user), domain/admin management (9 — one hardcoded domain), follow-up conversation context (10), broken-source detection (11).
- **One pilot domain, hardcoded.** Don't generalize the corpus, auth, or domain handling — that's a Story 9 scope creep.

If a request would extend code beyond this MVP, flag it and propose a concept-doc deliverable instead of implementing it.

## Stack (planned — fix in Week 1, do not relitigate later)

The plan calls for the tech stack to be **fixed in Sprint 0 / Week 1** and not revisited. Current signals:

- `.gitignore` is configured for **Angular + TypeScript** (frontend).
- Plan mandates **Azure OpenAI EU** for the LLM (no on-prem experiment).
- Vector DB choice is open as of writing — pick one in W1, then commit.

Once the stack is fixed, replace this section with the actual choices and add the build/test/run commands. Until that happens, there are no build/test commands to document.

## Repository conventions

- **`Artefakten/Modul{N}Tag{M}/`** — course deliverables organised by module/day. New course-day deliverables go in a new `Modul{N}Tag{M}` subfolder; do not reorganise the historical ones.
- **Language:** project artefacts and folder names are in German (e.g. `Artefakten`, `Modul1Tag2`). Code identifiers and commit messages can be English or German — match the surrounding context.
- Empty subfolders in `Artefakten/` (e.g. `Modul1Tag1`, `Modul2Tag1`) are placeholders for upcoming course days. Git doesn't track empty dirs, so they may not appear in remote checkouts until populated.

## Working with the personas

The plan and stories are anchored on two personas — keep them in mind when making UX/scope tradeoffs:

- **Lara Fischer** — junior dev, 6 weeks in, primary user of Q&A. Cares about: trust, speed beats Slack, visible sources.
- **Stefan Brunner** — senior BA / domain owner, content curator. Cares about: low maintenance overhead, no false answers under his name.

The biggest project risk is **content rot** (Stefan stops curating → corpus drifts → trust collapses). Visible source citations and the "Weiß ich nicht" path exist to mitigate this — they are non-negotiable acceptance criteria for Story 1, not nice-to-haves.
