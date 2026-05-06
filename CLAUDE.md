# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

**LearnFlow**:Eine interne Lernplattform, die neuen Entwickler:innen, Requirements-Engineers und Tester:innen das fachliche Domänen- und Systemwissen historisch gewachsenen Fachanwendungen über quellenbelegte KI-Antworten und überprüfte Quizfragen zugänglich macht – auf Basis eines kuratierten, vom Fachbereich freigegebenen Lern-Korpus.

The repo is at the **start of Sprint 0** (tech spike). There is currently no application code — only kickoff artefacts under `Artefakten/`. The full background (problem statement, personas, user stories, risks, canvas, plan) lives in the prework documents and should be consulted before making non-trivial decisions:

- `Artefakten/Modul1Tag2/LearnFlow_Plan_15Wochen.md` — the binding 15-week / 360 h plan and scope
- `Artefakten/Modul1Tag2/LearnFlow_Kickoff_Doku.md`

## Hard constraints

tbd

## Stack 

tbd
## Repository conventions

- **`Artefakten/Modul{N}Tag{M}/`** — course deliverables organised by module/day. New course-day deliverables go in a new `Modul{N}Tag{M}` subfolder; do not reorganise the historical ones.
- **Language:** project artefacts and folder names are in German (e.g. `Artefakten`, `Modul1Tag2`). Code identifiers and commit messages can be English or German — match the surrounding context.
- Empty subfolders in `Artefakten/` (e.g. `Modul1Tag1`, `Modul2Tag1`) are placeholders for upcoming course days. Git doesn't track empty dirs, so they may not appear in remote checkouts until populated.
