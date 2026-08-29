"""Document parsing — extracts text blocks with their source metadata (T-12).

A block is one structural unit of the source: a PDF page, a DOCX or Markdown
paragraph. Blocks carry the metadata needed for later source attribution
(US-01) but know nothing about tokens — turning them into sized chunks is
app.services.chunking's job, which keeps both halves testable in isolation.
"""

import io
import re
from dataclasses import dataclass

import docx
import pypdf

from app.exceptions import UserFacingError

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MARKDOWN_CONTENT_TYPE = "text/markdown"

_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
_MD_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
# A soft hyphen (U+00AD) with a line break behind it is a word the typesetter
# split; only joining the halves makes the word searchable as one token.
_SOFT_HYPHEN_BREAK = re.compile(r"[ \t]*\xad[ \t]*\n[ \t]*")


@dataclass(frozen=True)
class ParsedBlock:
    """One structural unit of a document, with where it came from."""

    text: str
    page: int | None = None
    heading: str | None = None


def parse_document(content: bytes, content_type: str) -> list[ParsedBlock]:
    """Parse an uploaded document into text blocks.

    Raises UserFacingError for content types the upload endpoint does not allow.
    """
    parser = _PARSERS.get(content_type)
    if parser is None:
        raise UserFacingError(f"Nicht unterstützter Content-Type: {content_type}")
    return [b for b in parser(content) if b.text]


def _parse_pdf(content: bytes) -> list[ParsedBlock]:
    """One block per page. PDFs carry no reliable heading structure, so page
    numbers (1-based, as a reader sees them) are the only metadata."""
    reader = pypdf.PdfReader(io.BytesIO(content))
    return [
        ParsedBlock(text=_normalise(page.extract_text() or ""), page=number)
        for number, page in enumerate(reader.pages, start=1)
    ]


def _parse_docx(content: bytes) -> list[ParsedBlock]:
    """One block per paragraph. Heading styles set the running heading; Word
    has no page concept without rendering, so page stays None."""
    document = docx.Document(io.BytesIO(content))
    blocks: list[ParsedBlock] = []
    heading: str | None = None

    for paragraph in document.paragraphs:
        text = _normalise(paragraph.text)
        if not text:
            continue
        # python-docx maps localised built-in styles back to their English
        # names ("Überschrift 1" -> "Heading 1"), so matching in English is enough.
        style = (paragraph.style.name or "") if paragraph.style is not None else ""
        if style.lower().startswith(("heading", "title")):
            heading = text
            continue
        blocks.append(ParsedBlock(text=text, heading=heading))

    return blocks


def _parse_markdown(content: bytes) -> list[ParsedBlock]:
    """One block per paragraph, split on blank lines. ATX headings (`#`) set
    the running heading; `#` inside fenced code blocks is ignored."""
    blocks: list[ParsedBlock] = []
    heading: str | None = None
    paragraph: list[str] = []
    in_fence = False

    def flush() -> None:
        nonlocal paragraph
        text = _normalise("\n".join(paragraph))
        if text:
            blocks.append(ParsedBlock(text=text, heading=heading))
        paragraph = []

    for line in content.decode("utf-8", errors="replace").splitlines():
        if _MD_FENCE.match(line):
            in_fence = not in_fence
            paragraph.append(line)
            continue

        match = None if in_fence else _MD_HEADING.match(line)
        if match:
            flush()
            heading = match.group(1).strip() or None
        elif line.strip() or in_fence:
            paragraph.append(line)
        else:
            flush()

    flush()
    return blocks


def _normalise(text: str) -> str:
    """Collapse the whitespace noise that PDF extraction in particular leaves
    behind, while keeping paragraph breaks intact."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    # Every other soft hyphen sits inside a line, where the PDF drew it as a
    # visible hyphen ("SAMW\xadRichtlinien"). Dropping those as well would turn
    # "Spital\xad und" into "Spitalund", so they become what they render as.
    text = _SOFT_HYPHEN_BREAK.sub("", text).replace("\xad", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


_PARSERS = {
    PDF_CONTENT_TYPE: _parse_pdf,
    DOCX_CONTENT_TYPE: _parse_docx,
    MARKDOWN_CONTENT_TYPE: _parse_markdown,
}
