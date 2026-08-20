"""The deterministic stages of the confidence pipeline (ADR-008, T-17/T-19).

Stages 0 and 1 are the two gates that decide whether a question ever reaches an
LLM; stage 2 decides whether the answer it produced may be delivered. All three
are tested against exact numbers rather than ranges — they are thresholds, and a
test that tolerates a range would not notice one drifting.
"""

from app.services.confidence import (
    MIN_SEGMENT_WORDS,
    WEIGHT_EVIDENCE_DENSITY,
    WEIGHT_MEAN_SCORE,
    WEIGHT_TOP_SCORE,
    check_citations,
    compute_retrieval_confidence,
    passes_retrieval_gate,
)

THRESHOLD = 0.35
TOP_N = 5

# Five chunks went to the model, so [1]..[5] are the legal references.
CONTEXT_SIZE = 5


def test_gate_passes_when_one_chunk_reaches_the_threshold() -> None:
    assert passes_retrieval_gate([0.1, 0.2, 0.4], THRESHOLD) is True


def test_gate_passes_exactly_on_the_threshold() -> None:
    """ADR-008 tripwire: the comparison is >=, never >."""
    assert passes_retrieval_gate([THRESHOLD], THRESHOLD) is True


def test_gate_fails_when_every_chunk_is_below_the_threshold() -> None:
    assert passes_retrieval_gate([0.34, 0.2, 0.01], THRESHOLD) is False


def test_gate_fails_without_any_chunk() -> None:
    assert passes_retrieval_gate([], THRESHOLD) is False


def test_confidence_of_no_chunks_is_zero() -> None:
    detail = compute_retrieval_confidence([], THRESHOLD, TOP_N)

    assert (detail.top_score, detail.mean_score, detail.result, detail.count) == (0.0, 0.0, 0.0, 0)


def test_confidence_combines_the_three_signals() -> None:
    scores = [0.8, 0.6, 0.4]  # all three above the threshold, 3 of 5 planned

    detail = compute_retrieval_confidence(scores, THRESHOLD, TOP_N)

    assert detail.top_score == 0.8
    assert detail.mean_score == 0.6
    assert detail.evidence_density == 0.6
    expected = WEIGHT_TOP_SCORE * 0.8 + WEIGHT_MEAN_SCORE * 0.6 + WEIGHT_EVIDENCE_DENSITY * 0.6
    assert detail.result == round(expected, 4)
    assert detail.count == 3


def test_top_score_is_the_best_chunk_not_the_first() -> None:
    """The context is ordered by RRF rank, so the first chunk need not be closest."""
    detail = compute_retrieval_confidence([0.5, 0.9], THRESHOLD, TOP_N)

    assert detail.top_score == 0.9


def test_chunks_below_the_threshold_do_not_count_as_evidence() -> None:
    detail = compute_retrieval_confidence([0.9, 0.1, 0.1, 0.1, 0.1], THRESHOLD, TOP_N)

    assert detail.evidence_density == 0.2  # only one of five carries evidence
    assert detail.mean_score == 0.26  # but every chunk still drags the mean down


def test_evidence_density_is_capped_at_one() -> None:
    """A larger context must not inflate the score beyond a full evidence base."""
    detail = compute_retrieval_confidence([0.9] * 8, THRESHOLD, TOP_N)

    assert detail.evidence_density == 1.0


def test_weak_retrieval_stays_below_the_seeded_gate() -> None:
    """Regression guard: barely-above-threshold chunks must not pass stage 1."""
    detail = compute_retrieval_confidence([0.36, 0.35], THRESHOLD, TOP_N)

    assert detail.result < 0.40


# ── Stage 2: Grounding-/Citation-Check (T-19) ───────────────────────────────


def test_every_sentence_backed_is_full_coverage() -> None:
    detail = check_citations(
        "Der EU AI Act regelt Hochrisiko-Systeme [1]. Er gilt ab 2026 [2].", CONTEXT_SIZE
    )

    assert detail.coverage == 1.0
    assert (detail.segments, detail.covered) == (2, 2)
    assert detail.referenced == (1, 2)
    assert detail.valid is True


def test_an_unbacked_sentence_halves_the_coverage() -> None:
    detail = check_citations(
        "Erste Aussage mit einem Beleg [1]. Zweite Aussage ganz ohne jeden Beleg.", CONTEXT_SIZE
    )

    assert detail.coverage == 0.5
    assert (detail.segments, detail.covered) == (2, 1)


def test_an_answer_without_any_reference_has_no_coverage() -> None:
    """AK 1: an answer that cites nothing carries no source reference at all."""
    detail = check_citations(
        "Der EU AI Act regelt Hochrisiko-Systeme umfassend und im Detail.", CONTEXT_SIZE
    )

    assert detail.coverage == 0.0
    assert detail.referenced == ()
    # Still "valid": nothing was invented, there is simply nothing to check.
    # The coverage threshold is what suppresses this one.
    assert detail.valid is True


def test_a_reference_past_the_context_is_fabricated() -> None:
    """AK 2: [7] out of five delivered chunks points at a source that never existed."""
    detail = check_citations("Das steht so im Dokument [7].", CONTEXT_SIZE)

    assert detail.valid is False
    assert detail.fabricated == (7,)


def test_reference_zero_is_fabricated() -> None:
    """The numbering starts at 1, so [0] is not an off-by-one to be forgiven."""
    detail = check_citations("Das steht so im Dokument [0].", CONTEXT_SIZE)

    assert detail.valid is False


def test_a_fabricated_reference_backs_nothing() -> None:
    """An invented source must not count as a backing, on top of invalidating."""
    detail = check_citations(
        "Erste Aussage mit gutem Beleg [1]. Zweite Aussage mit erfundenem Beleg [9].",
        CONTEXT_SIZE,
    )

    assert detail.coverage == 0.5  # the [9] segment counts as unbacked
    assert detail.referenced == (1,)
    assert detail.fabricated == (9,)
    assert detail.valid is False


def test_a_fabricated_reference_counts_from_a_segment_too_short_to_score() -> None:
    """An invented source is a model failure wherever it stands."""
    detail = check_citations("Eine erste, ausreichend lange Aussage [1].\nNein [9]", CONTEXT_SIZE)

    assert detail.coverage == 1.0  # the short fragment never entered the count
    assert detail.valid is False


def test_multiple_references_on_one_statement() -> None:
    detail = check_citations("Das ergibt sich aus mehreren Stellen [1][3].", CONTEXT_SIZE)

    assert detail.coverage == 1.0
    assert detail.referenced == (1, 3)


def test_the_comma_form_is_tolerated_and_validated_per_index() -> None:
    """[1, 2] is not what the prompt asks for, but each index is still checked."""
    backed = check_citations("Das ergibt sich aus zwei Stellen [1, 2].", CONTEXT_SIZE)
    assert backed.referenced == (1, 2)
    assert backed.valid is True

    invented = check_citations("Das ergibt sich aus zwei Stellen [1, 9].", CONTEXT_SIZE)
    assert invented.fabricated == (9,)
    assert invented.valid is False


def test_a_non_numeric_bracket_is_neither_a_reference_nor_a_fabrication() -> None:
    """"[sic]" is punctuation; reading it as an invented source would suppress prose."""
    detail = check_citations("Die Vorschrift nennt das [sic] ausdruecklich so [1].", CONTEXT_SIZE)

    assert detail.valid is True
    assert detail.referenced == (1,)
    assert detail.coverage == 1.0


def test_german_abbreviations_do_not_split_a_sentence() -> None:
    """Without the abbreviation list this is five segments, four of them unbacked."""
    detail = check_citations(
        "Gemaess Art. 5 Abs. 2 ist z. B. Social Scoring untersagt [1].", CONTEXT_SIZE
    )

    assert detail.segments == 1
    assert detail.coverage == 1.0


def test_a_reference_behind_the_full_stop_still_backs_its_claim() -> None:
    """Models write "Aussage. [1]"; the [1] belongs to the sentence before it."""
    detail = check_citations(
        "Der Act regelt die Aufsicht nicht abschliessend. [1] Weitere Angaben fehlen [2].",
        CONTEXT_SIZE,
    )

    assert (detail.segments, detail.covered) == (2, 2)
    assert detail.coverage == 1.0


def test_each_bullet_is_its_own_segment() -> None:
    detail = check_citations(
        "- Verbotene Praktiken sind abschliessend geregelt [1]\n"
        "- Hochrisiko-Systeme brauchen eine Konformitaetsbewertung",
        CONTEXT_SIZE,
    )

    assert (detail.segments, detail.covered) == (2, 1)
    assert detail.coverage == 0.5


def test_a_heading_neither_helps_nor_hurts_the_coverage() -> None:
    """A structural fragment is not a claim, so it must not count as unbacked."""
    detail = check_citations(
        "Zusammenfassung\nDer Act regelt Hochrisiko-Systeme umfassend [1].", CONTEXT_SIZE
    )

    assert (detail.segments, detail.covered) == (1, 1)
    assert detail.coverage == 1.0


def test_an_answer_of_nothing_but_fragments_has_no_coverage() -> None:
    """Fail-closed: no substantive segment means nothing was verifiably answered."""
    short = " ".join(["Wort"] * (MIN_SEGMENT_WORDS - 1))
    detail = check_citations(f"{short} [1]", CONTEXT_SIZE)

    assert detail.segments == 0
    assert detail.coverage == 0.0


def test_an_empty_answer_has_no_coverage() -> None:
    detail = check_citations("", CONTEXT_SIZE)

    assert (detail.segments, detail.covered, detail.coverage) == (0, 0, 0.0)
    assert detail.valid is True


def test_a_bullets_own_leading_reference_stays_with_its_bullet() -> None:
    """A line break is a segment boundary, so nothing moves across one.

    Regression: the trailing-reference repair used to run over the flattened
    list and pulled each bullet's "[n]" onto the bullet above it, leaving the
    last one unbacked — two fully cited bullets came out at 0.5, exactly on the
    seeded threshold.
    """
    detail = check_citations(
        "- [1] Verbotene Praktiken sind abschliessend geregelt\n"
        "- [2] Hochrisiko-Systeme brauchen eine Konformitaetsbewertung",
        CONTEXT_SIZE,
    )

    assert (detail.segments, detail.covered) == (2, 2)
    assert detail.coverage == 1.0


def test_a_single_uppercase_letter_still_ends_a_sentence() -> None:
    """Regression, and it was the fail-open direction.

    "Anhang A." is not an abbreviation. Reading it as one glued the next
    sentence on and let *its* citation back the unbacked claim in front of it.
    """
    detail = check_citations(
        "Die Pflicht gilt fuer Anhang A. Weitere Pflichten folgen daraus [1].", CONTEXT_SIZE
    )

    assert detail.segments == 2
    assert detail.coverage == 0.5


def test_the_letter_pair_abbreviations_still_hold_a_sentence_together() -> None:
    """The counterpart to the test above: "z. B." must not split."""
    for answer in (
        "Verboten ist z. B. Social Scoring nach diesen Vorgaben [1].",
        "Das ist i. S. v. Artikel 3 zu verstehen und gilt so [1].",
        "Betroffen sind u. a. Anbieter und Betreiber solcher Systeme [1].",
    ):
        detail = check_citations(answer, CONTEXT_SIZE)

        assert detail.segments == 1, answer
        assert detail.coverage == 1.0, answer
