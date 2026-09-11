"""T-56: eval/metrics.py isoliert getestet, ohne Stack und ohne LLM (DoD
Kriterium 3). Synthetische Citations/Chunks in derselben Form, in der
`httpx.Response.json()` sie aus `QueryResponse`/`DebugInfo` liefert.
"""

from eval.metrics import check_hallucination, retrieval_metrics

CORPUS_FILENAME = "SKOS-Richtlinien_-_Version_vom_1.1.2026.pdf"
OTHER_FILENAME = "EU_AI_ACT_OJ_L_202401689_DE_TXT.pdf"


def _citation(index: int, filename: str, page: int) -> dict:
    return {
        "chunk_id": f"chunk-{index}",
        "document_id": "doc-1",
        "filename": filename,
        "page": page,
        "heading": None,
        "excerpt": "…",
        "index": index,
    }


class TestCheckHallucination:
    def test_grounded_answer_is_not_hallucinated(self) -> None:
        citations = [_citation(1, CORPUS_FILENAME, 40)]

        verdict = check_hallucination(
            answer="Der GBL umfasst neun Positionen [1].",
            citations=citations,
            corpus_filename=CORPUS_FILENAME,
            expected_pages=(40, 41),
        )

        assert verdict.hallucinated is False
        assert verdict.reason is None
        assert verdict.grounded_in_expected_pages is True

    def test_answer_backed_by_expected_document_but_other_page_is_not_hallucinated(self) -> None:
        """H1/H2 do not gate on the expected pages -- an answer correctly
        grounded in the promised document, just on a page other than the one
        this particular question expects, is not a hallucination (moduledoc).
        """
        citations = [_citation(1, CORPUS_FILENAME, 99)]

        verdict = check_hallucination(
            answer="Antwort [1].",
            citations=citations,
            corpus_filename=CORPUS_FILENAME,
            expected_pages=(40, 41),
        )

        assert verdict.hallucinated is False
        assert verdict.grounded_in_expected_pages is False

    def test_h1_invalid_citation_is_hallucinated(self) -> None:
        """A reference outside 1..citation_count -- an invented source."""
        citations = [_citation(1, CORPUS_FILENAME, 40)]

        verdict = check_hallucination(
            answer="Antwort [1][5].",
            citations=citations,
            corpus_filename=CORPUS_FILENAME,
            expected_pages=(40,),
        )

        assert verdict.hallucinated is True
        assert verdict.reason == "citation_invalid"
        assert verdict.grounded_in_expected_pages is False

    def test_h2_wrong_document_is_hallucinated(self) -> None:
        """Belegt, aber aus einem anderen Dokument als dem zugesagten --
        die Klasse aus EvalAnalysis/2026-09-10_Befunde.md Punkt 4."""
        citations = [_citation(1, OTHER_FILENAME, 45)]

        verdict = check_hallucination(
            answer="Antwort [1].",
            citations=citations,
            corpus_filename=CORPUS_FILENAME,
            expected_pages=(40,),
        )

        assert verdict.hallucinated is True
        assert verdict.reason == "wrong_document"

    def test_answer_using_no_reference_at_all_is_hallucinated(self) -> None:
        """An answer that cites nothing has nothing tying it to the corpus."""
        citations = [_citation(1, CORPUS_FILENAME, 40)]

        verdict = check_hallucination(
            answer="Eine Antwort ganz ohne Fussnote.",
            citations=citations,
            corpus_filename=CORPUS_FILENAME,
            expected_pages=(40,),
        )

        assert verdict.hallucinated is True
        assert verdict.reason == "wrong_document"

    def test_unused_context_citation_does_not_save_a_wrong_document_answer(self) -> None:
        """`citations` carries the whole delivered context, not only what the
        answer actually used -- a correct source sitting unused in the list
        must not launder a claim backed by a different document."""
        citations = [
            _citation(1, OTHER_FILENAME, 45),
            _citation(2, CORPUS_FILENAME, 40),
        ]

        verdict = check_hallucination(
            answer="Antwort [1].",
            citations=citations,
            corpus_filename=CORPUS_FILENAME,
            expected_pages=(40,),
        )

        assert verdict.hallucinated is True
        assert verdict.reason == "wrong_document"


def _chunk(filename: str, page: int) -> dict:
    return {"filename": filename, "page": page}


class TestRetrievalMetrics:
    def test_full_recall_and_precision(self) -> None:
        chunks = [_chunk(CORPUS_FILENAME, 40), _chunk(CORPUS_FILENAME, 41)]

        m = retrieval_metrics(chunks, corpus_filename=CORPUS_FILENAME, expected_pages=(40, 41))

        assert m.recall == 1.0
        assert m.precision == 1.0
        assert m.mrr == 1.0
        assert m.hits == 2
        assert m.considered == 2

    def test_partial_recall_needs_both_pages_of_a_multi_page_source(self) -> None:
        """expected_pages is a list because chunking.py makes page breaks hard
        chunk boundaries -- one hit page out of two expected is half, not
        full, recall (module docstring)."""
        chunks = [_chunk(CORPUS_FILENAME, 40), _chunk(OTHER_FILENAME, 1)]

        m = retrieval_metrics(chunks, corpus_filename=CORPUS_FILENAME, expected_pages=(40, 41))

        assert m.recall == 0.5
        assert m.precision == 0.5
        assert m.hits == 1

    def test_no_hit_is_zero_recall_and_precision(self) -> None:
        chunks = [_chunk(OTHER_FILENAME, 1), _chunk(CORPUS_FILENAME, 99)]

        m = retrieval_metrics(chunks, corpus_filename=CORPUS_FILENAME, expected_pages=(40,))

        assert m.recall == 0.0
        assert m.precision == 0.0
        assert m.mrr == 0.0
        assert m.hits == 0

    def test_mrr_is_the_reciprocal_rank_of_the_first_hit(self) -> None:
        chunks = [
            _chunk(OTHER_FILENAME, 1),
            _chunk(OTHER_FILENAME, 2),
            _chunk(CORPUS_FILENAME, 40),
        ]

        m = retrieval_metrics(chunks, corpus_filename=CORPUS_FILENAME, expected_pages=(40,))

        assert m.mrr == 1 / 3

    def test_page_outside_the_expected_list_does_not_count_as_a_hit(self) -> None:
        chunks = [_chunk(CORPUS_FILENAME, 999)]

        m = retrieval_metrics(chunks, corpus_filename=CORPUS_FILENAME, expected_pages=(40, 41))

        assert m.hits == 0
        assert m.recall == 0.0

    def test_empty_chunk_list_is_zero_precision_not_a_crash(self) -> None:
        m = retrieval_metrics([], corpus_filename=CORPUS_FILENAME, expected_pages=(40,))

        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.mrr == 0.0
        assert m.considered == 0

    def test_duplicate_hit_pages_do_not_inflate_recall_above_one(self) -> None:
        """Several chunks of the same expected page (a split paragraph) count
        once towards page coverage, not once per chunk."""
        chunks = [_chunk(CORPUS_FILENAME, 40), _chunk(CORPUS_FILENAME, 40)]

        m = retrieval_metrics(chunks, corpus_filename=CORPUS_FILENAME, expected_pages=(40,))

        assert m.recall == 1.0
        assert m.hits == 2  # precision counts chunks, recall counts pages
