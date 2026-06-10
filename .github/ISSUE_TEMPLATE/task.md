---
name: Task
about: Entwicklungsaufgabe aus dem LearnFlow-Backlog
title: "[T-XX] <Kurzbeschreibung>"
labels: ""
assignees: ""
---

## Beschreibung

<!-- Was genau muss implementiert werden? Kontext und Ziel in 2–3 Sätzen. -->

## Akzeptanzkriterien

<!-- Direkt aus der User Story übernehmen. Jedes Kriterium muss einzeln prüfbar sein. -->

- [ ] 
- [ ] 
- [ ] 

## Definition of Done

<!-- Alle zutreffenden Punkte müssen vor dem Merge erfüllt sein. Vollständige DoD: Docs/07_Definition-of-Done.md -->

- [ ] Review durch eine zweite Person (nicht Autor/Prompter)
- [ ] CI grün: Lint + Type-Check + Tests (`make check`)
- [ ] Unit-Test für neue Logik vorhanden; RAG-Komponente isoliert aufrufbar *(nur bei Backend-Logik)*
- [ ] Eval-Gate nicht verschlechtert: Halluzinationsrate = 0 %, Out-of-Corpus-Refusal ≥ 90 % *(nur bei RAG-Pipeline-Änderungen)*
- [ ] Akzeptanzkriterien manuell durchgespielt im laufenden System
- [ ] Code-Qualität geprüft: kein Ballast, korrekte Modulzuordnung, keine unnötige Abstraktion
- [ ] ADR/Docs aktualisiert *(nur wenn ein Architekturentscheid berührt ist)*

## Metadaten

| Feld | Wert |
|---|---|
| **Story Points** | <!-- 1 / 2 / 3 / 5 / 8 --> |
| **Bereich** | <!-- Backend / Frontend / DB / DevOps --> |
| **Abhängig von** | <!-- T-XX, T-YY oder — --> |
| **Zugehörige Story** | <!-- US-XX --> |
