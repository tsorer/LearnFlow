"""Structure-aware, token-based chunking (ADR-007, T-12).

Splitting respects natural boundaries first (heading > paragraph > sentence >
line > word) and only falls back to the next finer boundary when a piece still
exceeds the token budget — so chunks never end mid-sentence.

The token counter is injectable: the worker uses tiktoken (matching the
embedding model, ADR-005), tests use a trivial counter to assert exact chunk
boundaries without a network round-trip for the BPE files.
"""

import functools
import itertools
import re
from collections.abc import Callable
from dataclasses import dataclass

import tiktoken

from app.exceptions import UserFacingError
from app.services.parsing import ParsedBlock

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64

# cl100k_base is the encoding of text-embedding-3-small (ADR-005), so token
# counts here match what the embedding API will charge and truncate on.
ENCODING_NAME = "cl100k_base"

TokenCounter = Callable[[str], int]

# Abbreviations that do not end a sentence — without them administrative German
# ("Art. 5", "Abs. 2") falls apart into fragments, which is exactly the
# vocabulary of the EU AI Act and the SKOS guidelines. Case-sensitive: extend
# with the forms the corpus actually contains. The spaced forms are listed
# letter by letter ("z", "B" for "z. B.") because each dot is a split candidate
# of its own. Counted in the pilot corpus: Art. 106x, Abs. 42x, z. B. 37x,
# bzw. 16x, d. h. 10x, vgl. 9x, usw. 5x, u. a. 4x, etc. 2x.
_ABBREVIATIONS = (
    "Art", "Abs", "Ziff", "Bst", "Buchst", "lit", "Nr", "Kap",
    "vgl", "Vgl", "bzw", "ca", "z", "B", "S", "Abb", "Tab",
    "d", "h", "u", "a", "usw", "etc",
)  # fmt: skip
# Each lookbehind sits *after* the punctuation, so it must include the dot:
# `(?<!\bArt)` would never match anything.
_NOT_AFTER_ABBREVIATION = "".join(rf"(?<!\b{abbr}\.)" for abbr in _ABBREVIATIONS)
_SENTENCE_END = re.compile(rf"(?<=[.!?…]){_NOT_AFTER_ABBREVIATION}\s+")

# Boundary priority. Sentences rank above single line breaks: in a PDF text
# layer a line break is a layout artifact that almost always falls mid-sentence,
# so splitting on it first would end chunks mid-sentence before the sentence
# splitter ever runs. Paragraph and line splits keep their separator when
# rejoined; sentence and word splits consumed whitespace, so they rejoin with
# a single space.
_SPLITTERS: list[tuple[Callable[[str], list[str]], str]] = [
    (lambda text: text.split("\n\n"), "\n\n"),
    (lambda text: _SENTENCE_END.split(text), " "),
    (lambda text: text.split("\n"), "\n"),
    (lambda text: text.split(" "), " "),
]


@dataclass(frozen=True)
class Chunk:
    """A token-sized slice of a document, ready to be persisted."""

    content: str
    chunk_index: int
    page: int | None = None
    heading: str | None = None


@functools.cache
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING_NAME)


def count_tokens(text: str) -> int:
    """Token count as the embedding model sees it (ADR-005)."""
    return len(_encoding().encode(text))


def chunk_blocks(
    blocks: list[ParsedBlock],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    count: TokenCounter = count_tokens,
) -> list[Chunk]:
    """Split parsed blocks into chunks of at most `chunk_size` tokens.

    Blocks sharing the same (heading, page) form a section; section borders are
    hard chunk borders, so a chunk never mixes two headings or two PDF pages
    and its metadata is exact rather than approximate.
    """
    # Both values come from the config table, so a bad one is an operator
    # mistake rather than a bad document. The message reaches the uploader
    # (worker/main.py writes it to documents.error_message), and the prefix is
    # what keeps them from looking for the fault in their own file.
    if chunk_size <= 0:
        raise UserFacingError("Chunk-Konfiguration ungültig: chunk_size muss grösser als 0 sein")
    if not 0 <= chunk_overlap < chunk_size:
        raise UserFacingError(
            "Chunk-Konfiguration ungültig: chunk_overlap muss zwischen 0 und chunk_size liegen"
        )

    chunks: list[Chunk] = []
    for (heading, page), section in itertools.groupby(blocks, key=lambda b: (b.heading, b.page)):
        text = "\n\n".join(block.text for block in section)
        for piece in _split(text, chunk_size, chunk_overlap, count, level=0):
            chunks.append(
                Chunk(content=piece, chunk_index=len(chunks), page=page, heading=heading)
            )
    return chunks


def _split(text: str, size: int, overlap: int, count: TokenCounter, level: int) -> list[str]:
    """Recursively split `text` until every piece fits into `size` tokens."""
    if not text.strip():
        return []
    if count(text) <= size:
        return [text]
    if level >= len(_SPLITTERS):
        return _force_split(text, size, count)

    splitter, joiner = _SPLITTERS[level]
    pieces: list[str] = []
    pending: list[str] = []

    for part in splitter(text):
        if not part.strip():
            continue
        if count(part) <= size:
            pending.append(part)
            continue
        # Part is still too large: flush what fits, then split it finer.
        pieces.extend(_merge(pending, joiner, size, overlap, count))
        pending = []
        pieces.extend(_split(part, size, overlap, count, level + 1))

    pieces.extend(_merge(pending, joiner, size, overlap, count))
    return pieces


def _merge(
    parts: list[str], joiner: str, size: int, overlap: int, count: TokenCounter
) -> list[str]:
    """Greedily pack parts into chunks, carrying `overlap` tokens forward."""
    if not parts:
        return []

    sized = [(part, count(part)) for part in parts]
    chunks: list[str] = []
    current: list[tuple[str, int]] = []

    for part, tokens in sized:
        if current and _total(current) + tokens + 1 > size:
            chunks.append(joiner.join(text for text, _ in current))
            current = _overlap_tail(current, overlap)
            if current and _total(current) + tokens + 1 > size:
                # The next part leaves no room for the overlap — drop it rather
                # than exceed the chunk size.
                current = []
        current.append((part, tokens))

    if current:
        chunks.append(joiner.join(text for text, _ in current))
    return chunks


def _total(items: list[tuple[str, int]]) -> int:
    """Token total including one token per joiner — an upper bound, so chunks
    stay under the limit rather than drifting over it."""
    return sum(tokens for _, tokens in items) + max(0, len(items) - 1)


def _overlap_tail(items: list[tuple[str, int]], overlap: int) -> list[tuple[str, int]]:
    """Trailing parts of a chunk that fit within the overlap budget."""
    tail: list[tuple[str, int]] = []
    for item in reversed(items):
        if _total([item, *tail]) > overlap:
            break
        tail.insert(0, item)
    return tail


def _force_split(text: str, size: int, count: TokenCounter) -> list[str]:
    """Last resort for a single word larger than a whole chunk — e.g. a PDF
    whose text layer has no spaces. Slices by characters using the measured
    token/character ratio, narrowing until every slice fits."""
    width = max(1, len(text) * size // count(text))
    while width > 1:
        parts = [text[i : i + width] for i in range(0, len(text), width)]
        if all(count(part) <= size for part in parts):
            return parts
        width = width * 4 // 5
    return list(text)
