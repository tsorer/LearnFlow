import re

import pytest

from app.services.chunking import chunk_blocks
from app.services.parsing import ParsedBlock


# Trivial stand-in for tiktoken: one word = one token. Keeps chunk boundaries
# predictable in assertions and the test suite free of the BPE download.
def words(text: str) -> int:
    return len(text.split())


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=\.)\s+", text) if s]


# Six "tokens" each.
SENTENCES = [f"Satz nummer {i} mit sechs Wörtern." for i in range(1, 21)]


def test_short_document_becomes_one_chunk() -> None:
    blocks = [ParsedBlock(text="Ein kurzer Absatz.", page=3, heading="Titel")]

    chunks = chunk_blocks(blocks, chunk_size=20, chunk_overlap=6, count=words)

    assert len(chunks) == 1
    assert chunks[0].content == "Ein kurzer Absatz."
    assert chunks[0].chunk_index == 0
    assert (chunks[0].page, chunks[0].heading) == (3, "Titel")


def test_heading_change_is_a_hard_chunk_border() -> None:
    blocks = [
        ParsedBlock(text="Erster Absatz.", heading="A"),
        ParsedBlock(text="Zweiter Absatz.", heading="A"),
        ParsedBlock(text="Dritter Absatz.", heading="B"),
    ]

    chunks = chunk_blocks(blocks, chunk_size=100, chunk_overlap=10, count=words)

    assert [c.heading for c in chunks] == ["A", "B"]
    assert chunks[0].content == "Erster Absatz.\n\nZweiter Absatz."
    assert chunks[1].content == "Dritter Absatz."


def test_page_change_is_a_hard_chunk_border() -> None:
    blocks = [
        ParsedBlock(text="Seite eins.", page=1),
        ParsedBlock(text="Seite zwei.", page=2),
    ]

    chunks = chunk_blocks(blocks, chunk_size=100, chunk_overlap=10, count=words)

    assert [(c.page, c.content) for c in chunks] == [(1, "Seite eins."), (2, "Seite zwei.")]


def test_long_text_is_split_within_size_and_never_mid_sentence() -> None:
    blocks = [ParsedBlock(text=" ".join(SENTENCES))]

    chunks = chunk_blocks(blocks, chunk_size=20, chunk_overlap=6, count=words)

    assert len(chunks) > 1
    assert all(words(c.content) <= 20 for c in chunks)
    assert all(c.content.endswith(".") for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_abbreviations_do_not_end_a_chunk() -> None:
    # "Art. 5", "Abs. 2" — the vocabulary of the EU AI Act and the SKOS
    # guidelines. A naive split after every dot ends chunks on "Art.".
    text = " ".join(f"Nach Art. {i} gilt Regel Nummer {i} zwingend." for i in range(1, 21))

    chunks = chunk_blocks([ParsedBlock(text=text)], chunk_size=20, chunk_overlap=6, count=words)

    assert len(chunks) > 1
    assert not any(c.content.rstrip().endswith(("Art.", "Abs.")) for c in chunks)


def test_line_breaks_do_not_end_a_chunk_mid_sentence() -> None:
    # A PDF text layer wraps sentences across lines; the break is a layout
    # artifact, not a sentence boundary.
    page = "\n".join(f"Satz nummer {i} mit\nsechs Wörtern." for i in range(1, 21))

    chunks = chunk_blocks(
        [ParsedBlock(text=page, page=1)], chunk_size=20, chunk_overlap=6, count=words
    )

    assert len(chunks) > 1
    assert all(words(c.content) <= 20 for c in chunks)
    assert all(c.content.rstrip().endswith(".") for c in chunks)


def test_consecutive_chunks_overlap() -> None:
    blocks = [ParsedBlock(text=" ".join(SENTENCES))]

    chunks = chunk_blocks(blocks, chunk_size=20, chunk_overlap=6, count=words)

    # One sentence is exactly the overlap budget, so it repeats in the next chunk.
    for previous, following in zip(chunks, chunks[1:], strict=False):
        assert sentences(previous.content)[-1] == sentences(following.content)[0]


def test_zero_overlap_repeats_nothing() -> None:
    blocks = [ParsedBlock(text=" ".join(SENTENCES))]

    chunks = chunk_blocks(blocks, chunk_size=20, chunk_overlap=0, count=words)

    for previous, following in zip(chunks, chunks[1:], strict=False):
        assert sentences(previous.content)[-1] != sentences(following.content)[0]


def test_word_longer_than_a_chunk_is_force_split() -> None:
    # No whitespace to split on — e.g. a PDF text layer without spaces.
    blocks = [ParsedBlock(text="a" * 250)]

    chunks = chunk_blocks(blocks, chunk_size=30, chunk_overlap=5, count=len)

    assert len(chunks) > 1
    assert all(len(c.content) <= 30 for c in chunks)
    assert "".join(c.content for c in chunks) == "a" * 250


def test_no_blocks_yields_no_chunks() -> None:
    assert chunk_blocks([], chunk_size=20, chunk_overlap=6, count=words) == []


@pytest.mark.parametrize(("chunk_size", "chunk_overlap"), [(0, 0), (10, 10), (10, -1)])
def test_invalid_parameters_are_rejected(chunk_size: int, chunk_overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_blocks(
            [ParsedBlock(text="Text.")],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            count=words,
        )
