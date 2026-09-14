"""T-56: reine Metrik-Logik für den In-Corpus-Eval (ADR-009 Abschnitt 2).

Kein HTTP, keine DB, kein LLM — nur Funktionen über eine bereits abgerufene
`QueryResponse` (als dict, wie `httpx.Response.json()` sie liefert) und die
`expected_source`-Zusage aus dem Gold-Dataset. Getrennt vom Testmodul
(`eval/test_in_corpus_quality.py`), damit jede Metrik isoliert testbar ist
(DoD Kriterium 3) und ohne laufenden Stack läuft — `tests/test_eval_metrics.py`
deckt das mit synthetischen Antworten ab, ohne einen Provider zu brauchen.

## Halluzination (ADR-009: "primär deterministisch über Citation-/Grounding-Checks")

Eine *ausgelieferte* Antwort gilt als halluziniert, wenn mindestens eine der
folgenden zwei Bedingungen zutrifft:

  H1 — `CitationDetail.valid` ist False: eine der `[n]`-Referenzen im
       Antworttext zeigt auf keinen der mitgelieferten Kontext-Chunks. Die
       Pipeline unterdrückt das bereits (ADR-008, `citation_invalid`); ein
       Treffer hier bei einer *ausgelieferten* Antwort wäre ein Pipeline-
       Fehler, kein normaler Fall — die Prüfung steht trotzdem hier, fail-
       closed, statt sich blind auf die Pipeline zu verlassen.
  H2 — keine der im Antworttext tatsächlich referenzierten Citations (nicht:
       der gesamten mitgelieferten Liste — die enthält auch ungenutzten
       Kontext) stammt aus dem Korpusdokument, das `questions[].corpus` für
       diese Frage zusagt.

`check_citations` (app/services/confidence.py, Stufe 2) liefert bereits die
Menge der tatsächlich referenzierten Indizes (`referenced`) — dieses Modul
importiert sie, statt die Regex ein zweites Mal zu schreiben, und schneidet
`citations` darauf zu, um zwischen "im Kontext" und "in der Antwort benutzt"
zu trennen.

Was H1/H2 NICHT prüfen: ob die Aussage inhaltlich mit der Quelle
übereinstimmt (Faithfulness im RAGAS-Sinn). Das ist eine LLM-Judge-Frage, und
ADR-009 hält sie bewusst aus den harten Gates heraus ("zu wichtig, um sie
einem Judge allein zu überlassen"). H1/H2 demonstrieren eine obere Schranke
auf einer mechanisch erkennbaren Fehlerklasse — "die Antwort stützt sich ganz
auf ein anderes Dokument als das fachlich zugesagte", die Klasse aus
`EvalAnalysis/2026-09-10_Befunde.md` Punkt 4 (`AIA-OOC-07`: belegt, vom
Self-Check mit GEDECKT bestätigt, aber das falsche Rechtsdokument) — nicht
Halluzination im umgangssprachlichen Sinn. `grounded_in_expected_pages` ist
deshalb bewusst NICHT Teil der H1/H2-Entscheidung: das ist Recall-Territorium
(Gruppe B unten), eine inhaltlich richtige Antwort über eine andere, ebenfalls
im zugesagten Dokument belegte Seite darf nicht als Halluzination zählen.

## Retrieval-Güte (ADR-009 Abschnitt 2B)

Der Join-Vertrag aus dem Dataset-Kopf: ein Treffer ist ein Chunk mit
`filename == corpora[corpus].filename` **und** `page in expected_source.pages`.
Zwei Schnitte über dieselbe `debug.chunks`-Liste (Fusionsreihenfolge, siehe
`ChunkDebugInfo` in openapi.yaml):

  - **top-k** (die ganze Liste) — die Zahl für die Retrieval-Kalibrierung
    (ADR-007: `retrieval_top_k`, `rrf_k`).
  - **Kontext** (nur `in_top_n`) — die Zahl für die Antwortqualität: das ist,
    was das LLM tatsächlich gesehen hat.

Recall ist Seitendeckung, nicht Chunk-Trefferquote: `expected_source.pages`
ist eine Liste, weil `chunking.py` Seitengrenzen zu harten Chunkgrenzen macht
— eine Antwort über einen Seitenumbruch braucht Chunks von beiden Seiten. Eine
Trefferquote über Chunks würde das verdecken: fünf Chunks von derselben
erwarteten Seite zählen bei einer Trefferquote wie voller Recall, obwohl eine
zweite erwartete Seite komplett fehlt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.confidence import check_citations


@dataclass(frozen=True)
class HallucinationVerdict:
    """Ergebnis von H1/H2 für eine ausgelieferte Antwort."""

    hallucinated: bool
    #: "citation_invalid" (H1), "wrong_document" (H2), None wenn nicht
    #: halluziniert. Eine ausgelieferte Antwort ohne eine einzige benutzte
    #: Referenz kommt in der Praxis nicht vor (Stufe 2 verlangt covered > 0 für
    #: Coverage > 0, und Coverage unter der Schwelle unterdrückt bereits) --
    #: dieser Fall zählt trotzdem als "wrong_document", fail-closed, statt eine
    #: unbelegte Antwort stillschweigend als "nicht halluziniert" zu werten.
    reason: str | None
    #: Zusatzsignal, nicht Teil der H1/H2-Entscheidung -- siehe Moduldoc.
    grounded_in_expected_pages: bool


def check_hallucination(
    *,
    answer: str,
    citations: list[dict[str, Any]],
    corpus_filename: str,
    expected_pages: tuple[int, ...],
) -> HallucinationVerdict:
    """H1/H2 für eine ausgelieferte Antwort.

    Nur für `suppressed: false` aufrufen -- eine unterdrückte Antwort hat
    keinen Antworttext, über den H1/H2 etwas aussagen könnten (siehe
    False-Suppression stattdessen).
    """
    detail = check_citations(answer, citation_count=len(citations))
    if not detail.valid:
        return HallucinationVerdict(
            hallucinated=True, reason="citation_invalid", grounded_in_expected_pages=False
        )

    by_index = {citation["index"]: citation for citation in citations}
    used = [by_index[index] for index in detail.referenced if index in by_index]

    if not used or not any(citation["filename"] == corpus_filename for citation in used):
        return HallucinationVerdict(
            hallucinated=True, reason="wrong_document", grounded_in_expected_pages=False
        )

    grounded = any(
        citation["filename"] == corpus_filename and citation.get("page") in expected_pages
        for citation in used
    )
    return HallucinationVerdict(
        hallucinated=False, reason=None, grounded_in_expected_pages=grounded
    )


@dataclass(frozen=True)
class RetrievalMetrics:
    """Context-Recall/Precision/MRR für einen Schnitt der Kandidatenliste."""

    #: None nur, wenn expected_pages leer ist -- kommt für in_corpus- und
    #: quellentragende adversarial-Fragen nicht vor
    #: (test_sources_use_the_anchor_their_corpus_declares erzwingt eine
    #: nicht-leere Liste).
    recall: float | None
    precision: float
    mrr: float
    hits: int
    considered: int


def _is_hit(chunk: dict[str, Any], corpus_filename: str, expected_pages: tuple[int, ...]) -> bool:
    return chunk.get("filename") == corpus_filename and chunk.get("page") in expected_pages


def retrieval_metrics(
    chunks: list[dict[str, Any]],
    *,
    corpus_filename: str,
    expected_pages: tuple[int, ...],
) -> RetrievalMetrics:
    """Recall/Precision/MRR über `chunks`, in der übergebenen Reihenfolge.

    `chunks` ist bereits der gewünschte Schnitt -- die ganze `debug.chunks`-
    Liste für top-k, oder die auf `in_top_n` gefilterte Teilliste für den
    Kontext. Reihenfolge ist die Fusionsreihenfolge (`rrf_score` absteigend),
    wie sie aus der Response kommt; diese Funktion sortiert nicht nach.
    """
    hit_pages = {
        chunk.get("page") for chunk in chunks if _is_hit(chunk, corpus_filename, expected_pages)
    }
    hits = sum(1 for chunk in chunks if _is_hit(chunk, corpus_filename, expected_pages))

    mrr = 0.0
    for rank, chunk in enumerate(chunks, start=1):
        if _is_hit(chunk, corpus_filename, expected_pages):
            mrr = 1.0 / rank
            break

    return RetrievalMetrics(
        recall=len(hit_pages) / len(expected_pages) if expected_pages else None,
        precision=hits / len(chunks) if chunks else 0.0,
        mrr=mrr,
        hits=hits,
        considered=len(chunks),
    )
