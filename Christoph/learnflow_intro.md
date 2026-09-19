---
slide_id: learnflow-intro
slide_type: introduction
language: de-CH
brand: LearnFlow
context: Interne RAG-Lernplattform
kicker: Projektvorstellung
title: Eine Frage. Eine Antwort mit Beleg.
---

**LearnFlow**  
_Interne RAG-Lernplattform_

# Eine Frage. Eine Antwort mit Beleg.

LearnFlow macht kuratiertes internes Fachwissen zugänglich. Eine mehrstufige Fail-closed-Prüfung blockiert Antworten ohne belastbare Evidenz.

## 0 % gemessene Halluzinationsrate

In-Corpus-Evaluation vom 11.09.2026 · 33 ausgelieferte Antworten

### Lara fragt

> Was bedeutet das Bedarfsdeckungsprinzip?

**Vertrauensprüfung: OK**

### LearnFlow antwortet

Sozialhilfe deckt einen aktuellen Bedarf oder behebt eine aktuelle Notlage. Leistungen gelten grundsätzlich für die Gegenwart und nicht rückwirkend für Schulden. **[1]**

#### Quelle [1]

**SKOS-Richtlinien**  
A.3 Prinzipien der Sozialhilfe · Seiten 6–8

**LearnFlow liefert die Antwort**  
Quellen und Konfidenz erfüllen die Freigaberegeln.

<!--
INTEGRATION NOTES

Purpose:
- Introduce LearnFlow through one concrete, source-backed interaction.
- Establish trust and the fail-closed principle as the product's defining characteristic.

Suggested semantic regions for a future HTML deck:
- brand: "LearnFlow"
- context: "Interne RAG-Lernplattform"
- kicker: "Projektvorstellung"
- headline: "Eine Frage. Eine Antwort mit Beleg."
- lead: the paragraph below the headline
- metric: "0 % gemessene Halluzinationsrate"
- metric_scope: evaluation date and sample size
- question_actor: "Lara"
- question: the blockquote
- answer_actor: "LearnFlow"
- answer: the sourced answer paragraph
- citation: source title and locator
- release_state: trust-check and release wording

Accuracy notes:
- The 0% figure is a measured result, not a universal guarantee.
- It covers 33 delivered answers in the in-corpus evaluation dated 11 September 2026.
- The evaluation detects the defined H1/H2 hallucination classes. It does not establish comprehensive faithfulness for every possible answer.
- The SKOS question, answer and locator come from gold-eval-dataset.yaml, item SKOS-PRINZ-02.

Project references:
- LearningCorpus/gold-eval-dataset.yaml, SKOS-PRINZ-02
- EvalAnalysis/2026-09-11_In-Corpus-Befunde.md
- Docs/04_ADR-008_Konfidenz-Pipeline.md
-->
