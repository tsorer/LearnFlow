"""Deterministic confidence stages of the answer pipeline (ADR-008, T-17…T-23).

Covered here are stage 0 (the retrieval gate from ADR-007), stage 1 (the
retrieval confidence), stage 2 (the grounding/citation check) and the composite
score those last two feed. All of it is pure functions — no database, no LLM, no
I/O. That is deliberate: they are the part of the reliability chain that must
stay reproducible and cheap to test, and stages 0 and 1 are what decides whether
an LLM is called at all.

The split in time is what separates them. Stages 0 and 1 read similarity scores
and run *before* the generation; stage 2 reads the generated text and runs
*after* it, which is why it takes an answer string rather than scores. Stage 3
(the self-check, T-25) is the one stage that is not deterministic and therefore
not in this module — it lives in app/services/self_check.py.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

# Weights of the stage-1 components. ADR-008 names the three signals but not
# their weighting; these are start values to be calibrated against the eval
# dataset (ADR-009), which is why they are constants with a name rather than
# literals inside the formula. They stay in code, not in the config table: the
# config table holds thresholds the pilot recalibrates, and a weight change
# alters the meaning of every stored confidence_score.
WEIGHT_TOP_SCORE = 0.5
WEIGHT_MEAN_SCORE = 0.3
WEIGHT_EVIDENCE_DENSITY = 0.2

# Scores are stored and shown; four decimals is well beyond what a cosine
# similarity meaningfully distinguishes and keeps assertions in tests exact.
SCORE_DIGITS = 4


@dataclass(frozen=True)
class RetrievalDetail:
    """Stage-1 result with its components, mirroring `RetrievalDetail` in the spec.

    The breakdown is not decoration: an admin looking at a suppressed answer
    needs to see *which* signal was weak, otherwise the thresholds cannot be
    calibrated from real questions.
    """

    top_score: float
    mean_score: float
    evidence_density: float
    result: float
    count: int


def passes_retrieval_gate(scores: Sequence[float], similarity_threshold: float) -> bool:
    """Stage 0: at least one chunk must reach the similarity threshold (ADR-007).

    `>=`, not `>` — the seeded threshold is the lowest value that still counts
    as evidence, and tightening it here would silently diverge from the value an
    operator reads in the config table.
    """
    return any(score >= similarity_threshold for score in scores)


def compute_retrieval_confidence(
    scores: Sequence[float],
    similarity_threshold: float,
    context_top_n: int,
) -> RetrievalDetail:
    """Stage 1: deterministic confidence from the similarity of the context chunks.

    `scores` are the similarities of the chunks that would go to the LLM, in
    context order. ADR-008 names three signals: the best chunk, the average of
    the top-n, and how many chunks actually carry evidence.
    """
    if not scores:
        return RetrievalDetail(
            top_score=0.0, mean_score=0.0, evidence_density=0.0, result=0.0, count=0
        )

    # max(), not scores[0]: the context is ordered by the RRF rank, which mixes
    # in the sparse ranking, so the first chunk is not necessarily the closest
    # one. "Maximale Similarity des Top-Chunks" (ADR-008) means the best chunk.
    top_score = max(scores)
    mean_score = sum(scores) / len(scores)

    # Evidence density measured against the *configured* context size, not
    # against the chunks that happened to be found: three good chunks out of a
    # planned five is a weaker footing than five out of five, and the score
    # should say so. Capped at 1.0 so raising retrieval_top_k cannot inflate it.
    above_threshold = sum(1 for score in scores if score >= similarity_threshold)
    evidence_density = min(above_threshold / context_top_n, 1.0) if context_top_n else 0.0

    result = (
        WEIGHT_TOP_SCORE * top_score
        + WEIGHT_MEAN_SCORE * mean_score
        + WEIGHT_EVIDENCE_DENSITY * evidence_density
    )

    return RetrievalDetail(
        top_score=round(top_score, SCORE_DIGITS),
        mean_score=round(mean_score, SCORE_DIGITS),
        evidence_density=round(evidence_density, SCORE_DIGITS),
        result=round(result, SCORE_DIGITS),
        count=len(scores),
    )


# ── Stage 2: Grounding-/Citation-Check (ADR-008, T-19) ──────────────────────

# The reference format the grounding prompt prescribes: [1], repeated as [1][2].
# The comma form [1, 2] is tolerated although the prompt does not ask for it —
# every index inside is still validated on its own, so tolerating it weakens
# nothing and avoids suppressing a correct answer over its punctuation. The
# range form [1-3] is deliberately *not* tolerated: expanding it would credit
# the answer with a reference the model never wrote, and a hyphen between digits
# is also how a document number is written.
#
# `\d+` and not a bounded `\d{1,3}` (review of PR #86): the digit count is not a
# meaningful boundary here. These numbers are *our* positional indices into the
# context list the prompt hands the model — 1..context_top_n, five by default —
# not document ids and not years, so every value outside that range is equally
# invalid whatever its length. A bounded pattern made "[2026]" invisible to the
# check: neither a reference nor a fabrication, so `valid` stayed True and the
# answer shipped, while the very same sentence with "[12]" was suppressed. That
# split the fail-closed rule along the digit count of the invented number.
_REFERENCE = re.compile(r"\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]")

# Split after .!? followed by whitespace. The whitespace is what makes "z.B."
# safe without any list — no space, no boundary; only the spaced "z. B." needs
# the abbreviations below.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

# The word that ended the previous fragment, used to undo a split that landed
# inside an abbreviation.
_TRAILING_WORD = re.compile(r"([^\W\d_]+)\s*[.!?]\s*$", re.UNICODE)

# "- ", "* ", "1. ", "2) " — stripped before the sentence split so the marker
# does not become a fragment of its own ("1." ends in a period like any other).
_LIST_MARKER = re.compile(r"^\s*(?:[-*•–]|\d{1,2}[.)])\s+")

# "z. B.", "d. h.", "u. a.", "i. S. v." — two single letters, each with a period.
# The pair is what identifies the uppercase half: matching "B." on its own would
# make an abbreviation out of every "Anhang A." too.
_LETTER_PAIR_ABBREVIATION = re.compile(r"(?:^|\s)[^\W\d_]\.\s*[^\W\d_]\.\s*$")

# German abbreviations that end in a period without ending a sentence. The
# single-letter halves of "z. B." and friends are handled by the pair above.
#
# `app/services/chunking.py` keeps a second list for the same language, and the
# two are deliberately not shared. That module splits the *document* text of a
# PDF layer, where a line break is a layout artifact to be ignored; this one
# splits *generated* answers, where a line break is a bullet and therefore a
# hard segment boundary. Its list is also case-sensitive and carries "B" and "S"
# as entries of their own, which is right for chunking and wrong here — reusing
# it would stop "Anhang B." from ending a sentence and let the next sentence's
# citation back an unbacked claim. The failure costs differ too: a missed split
# costs chunking a suboptimal boundary and costs this stage a delivered
# unbacked statement.
#
# What the two lists *should* share is vocabulary, and in that direction the
# corpus-counted entries of chunking.py win: a missing abbreviation splits one
# sentence into two here, and the second half comes out unbacked. That is
# fail-closed but needlessly suppresses correct answers, so the forms attested
# there are carried over.
_ABBREVIATIONS = frozenset(
    {
        "abb", "abs", "art", "bspw", "bst", "buchst", "bzw", "ca", "etc",
        "evtl", "ff", "gem", "ggf", "inkl", "kap", "lit", "nr", "sog", "tab",
        "usw", "vgl", "ziff",
    }
)

# Below this many words a segment is structure, not a claim: a heading, a
# "Fazit:", a bare bullet. Such a fragment neither counts as covered nor as
# uncovered — it is skipped entirely, so it can neither drag the coverage down
# nor inflate it. An answer made of nothing but such fragments has no countable
# segment at all and comes out at coverage 0.0 — which the caller suppresses for
# any `min_citation_coverage` above zero. A threshold of exactly 0.0 is a legal
# config value and switches the coverage gate off entirely, the same way a
# `similarity_threshold` of 0.0 switches off stage 0; that is an operator
# disabling a stage, not this constant failing open.
MIN_SEGMENT_WORDS = 4


@dataclass(frozen=True)
class CitationDetail:
    """Stage-2 result: how well the generated answer is backed by its sources.

    Two independent verdicts, because they mean different things operationally.
    `coverage` is a threshold question and calibratable via
    `min_citation_coverage`; `valid` is not — a reference to a chunk that was
    never delivered is a model failure, and no threshold makes it acceptable.
    """

    coverage: float
    segments: int
    covered: int
    # Sorted and de-duplicated: both lists exist to be read by a human in the
    # admin debug view, not to be counted.
    referenced: tuple[int, ...]
    fabricated: tuple[int, ...]
    valid: bool


def check_citations(answer: str, citation_count: int) -> CitationDetail:
    """Stage 2: measure citation coverage and validate every reference (ADR-008).

    `citation_count` is the number of context chunks handed to the model, which
    is also the highest legal reference: the prompt numbers the chunks 1..n and
    `Citation.index` uses the same numbering, so anything outside that range is
    a source the answer invented.

    Brackets that are not numeric — "[sic]", "[…]" — are neither references nor
    fabrications and are ignored. Reading them as invented references would
    suppress answers over ordinary punctuation.
    """
    referenced: set[int] = set()
    fabricated: set[int] = set()
    segments = 0
    covered = 0

    for segment in _segments(answer):
        indices = _references(segment)
        legal = {index for index in indices if 1 <= index <= citation_count}
        referenced |= legal
        # Collected before the length check below: an invented reference is a
        # model failure wherever it stands, including in a fragment too short to
        # count towards the coverage.
        fabricated |= indices - legal

        if _word_count(_REFERENCE.sub(" ", segment)) < MIN_SEGMENT_WORDS:
            continue

        segments += 1
        if legal:
            covered += 1

    return CitationDetail(
        coverage=round(covered / segments, SCORE_DIGITS) if segments else 0.0,
        segments=segments,
        covered=covered,
        referenced=tuple(sorted(referenced)),
        fabricated=tuple(sorted(fabricated)),
        valid=not fabricated,
    )


def _references(segment: str) -> set[int]:
    """Every index the segment cites, flattening the tolerated comma form."""
    return {
        int(number)
        for match in _REFERENCE.finditer(segment)
        for number in match.group(1).split(",")
    }


def _word_count(text: str) -> int:
    return len(text.split())


def _segments(answer: str) -> list[str]:
    """Split the answer into the units the coverage is measured over.

    A line break separates segments before any punctuation does, so a bullet
    list is one segment per bullet rather than one run-on sentence.
    """
    segments: list[str] = []
    for line in answer.splitlines():
        stripped = _LIST_MARKER.sub("", line).strip()
        if stripped:
            segments.extend(_sentences(stripped))
    return segments


def _sentences(line: str) -> list[str]:
    """Sentence-split one line, re-joining splits that fell in an abbreviation."""
    sentences: list[str] = []
    for fragment in _SENTENCE_BOUNDARY.split(line):
        if sentences and _ends_in_abbreviation(sentences[-1]):
            sentences[-1] = f"{sentences[-1]} {fragment}"
        else:
            sentences.append(fragment)
    # Per line, never across one. The repair below undoes a split *this* function
    # made; a line break was never such a split, and reaching over one would move
    # a bullet's own reference onto the bullet above it.
    return _attach_trailing_references(sentences)


def _ends_in_abbreviation(fragment: str) -> bool:
    match = _TRAILING_WORD.search(fragment)
    if match is None:
        return False
    word = match.group(1)
    if word.lower() in _ABBREVIATIONS:
        return True
    if len(word) != 1:
        return False
    # A single letter is an abbreviation only in context. The "z." of "z. B." is
    # lowercase and always one; an uppercase "A." is only one as the second half
    # of a pair. Treating every "Anhang A." as an abbreviation would glue the
    # next sentence onto it and let *its* citation back an unbacked claim — the
    # fail-open direction ADR-008 rules out.
    return word.islower() or _LETTER_PAIR_ABBREVIATION.search(fragment) is not None


def _attach_trailing_references(segments: list[str]) -> list[str]:
    """Move a reference that trails *behind* the full stop back to its claim.

    The prompt asks for "[1]" directly after the statement, and models mostly
    comply — but "Aussage. [1]" happens, and the sentence split puts that [1] at
    the head of the *next* segment. Left alone, that would count the claim as
    unbacked and the following sentence as backed twice over: one suppression
    and one false pass from a single misplaced space.

    Called per line, on the fragments of one sentence split. A reference at the
    start of a *line* is that line's own — "[1] Erster Punkt" in a bullet list —
    and moving it up would rob every bullet but the first of its backing.
    """
    attached: list[str] = []
    for segment in segments:
        leading = _leading_references(segment)
        if leading and attached:
            attached[-1] = f"{attached[-1]} {leading}"
            segment = segment[len(leading) :].lstrip()
        if segment:
            attached.append(segment)
    return attached


def _leading_references(segment: str) -> str:
    """The run of references at the start of a segment, "" if it starts with text."""
    end = position = 0
    while (match := _REFERENCE.match(segment, position)) is not None:
        end = position = match.end()
        # "[1] [2] Rest" is one run, not one reference and then text.
        while position < len(segment) and segment[position].isspace():
            position += 1
    return segment[:end]


# ── Komposit-Konfidenz & Bänder (ADR-008, T-23) ─────────────────────────────

# Weights of the composite. ADR-008 names the two inputs but not their
# weighting, so these are start values to be calibrated (ADR-009) — equal, which
# is the only split that does not assert something the pilot has not measured.
#
# In code, not in the `config` table, although the ADR text says otherwise: the
# table holds thresholds an operator recalibrates against a *fixed* scale, and a
# weight change moves the scale itself. Every `answers.confidence_score` written
# before such a change would silently stop being comparable with the ones after
# it, which is exactly the calibration basis ADR-009 needs. Same reasoning as
# WEIGHT_TOP_SCORE above; the ADR carries the correction as a Nachtrag.
WEIGHT_RETRIEVAL_CONFIDENCE = 0.5
WEIGHT_CITATION_COVERAGE = 0.5

# The wire values of `ConfidenceInfo.band`. A Literal rather than a str, so a
# renamed band fails the type check here instead of reaching the frontend as an
# unlabelled key. The constants carry the annotation for the same reason —
# without it they widen to `str` and the guarantee stops at this module.
Band = Literal["hoch", "mittel", "niedrig"]

BAND_HIGH: Band = "hoch"
BAND_MEDIUM: Band = "mittel"
BAND_LOW: Band = "niedrig"


@dataclass(frozen=True)
class CompositeDetail:
    """The displayed confidence and the two parts it was built from (US-02)."""

    result: float
    retrieval_score: float
    # None means stage 2 never ran, and the result is then the retrieval score
    # alone. Not 0.0: an answer that was never generated has no segments that
    # could be backed, and folding that into the score as "nothing was covered"
    # would push every pre-generation suppression into the lowest band for a
    # measurement that never happened.
    citation_coverage: float | None


def compute_composite(retrieval_score: float, citation_coverage: float | None) -> CompositeDetail:
    """Combine stage 1 and stage 2 into the confidence the user is shown."""
    if citation_coverage is None:
        return CompositeDetail(
            result=round(retrieval_score, SCORE_DIGITS),
            retrieval_score=retrieval_score,
            citation_coverage=None,
        )

    result = (
        WEIGHT_RETRIEVAL_CONFIDENCE * retrieval_score
        + WEIGHT_CITATION_COVERAGE * citation_coverage
    )
    return CompositeDetail(
        result=round(result, SCORE_DIGITS),
        retrieval_score=retrieval_score,
        citation_coverage=citation_coverage,
    )


def band_for(score: float, medium: float, high: float) -> Band:
    """Map the composite onto the three bands of ADR-008.

    `>=` on both limits, like every other threshold comparison in this module: a
    score exactly on the configured limit belongs to the band the operator set
    that limit for. `high` is checked first, so a degenerate configuration with
    medium == high still resolves — it collapses the middle band rather than
    producing a score that is in two bands at once.
    """
    if score >= high:
        return BAND_HIGH
    if score >= medium:
        return BAND_MEDIUM
    return BAND_LOW


def in_self_check_band(score: float, low: float, high: float) -> bool:
    """Whether the composite is close enough to the threshold to verify (stage 3).

    Half-open on purpose: `low` is inside the band and `high` is not. A score at
    `high` is the first one ADR-008 calls "klar hohe Konfidenz", and the whole
    point of the band is that those skip the second LLM call. That also makes
    low == high an empty band — stage 3 switched off — rather than a band that
    still catches a single value.
    """
    return low <= score < high
