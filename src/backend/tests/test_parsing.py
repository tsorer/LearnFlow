import pathlib

import pytest

from app.services.parsing import (
    DOCX_CONTENT_TYPE,
    MARKDOWN_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    parse_document,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_parse_pdf_yields_one_block_per_page() -> None:
    blocks = parse_document(load("sample.pdf"), PDF_CONTENT_TYPE)

    assert [b.page for b in blocks] == [1, 2]
    assert all(b.heading is None for b in blocks)
    assert "Hochrisiko-Systeme" in blocks[0].text
    assert "Aufsichtsbehörde" in blocks[1].text


def test_parse_docx_tracks_heading_styles() -> None:
    blocks = parse_document(load("sample.docx"), DOCX_CONTENT_TYPE)

    # Heading paragraphs are metadata, not content of their own.
    assert [b.heading for b in blocks] == ["Prüfprozess", "Prüfprozess", "Dokumentation"]
    assert blocks[0].text.startswith("Die Konformitätsbewertung")
    assert all(b.page is None for b in blocks)


def test_parse_markdown_tracks_headings_and_ignores_code_fences() -> None:
    blocks = parse_document(load("sample.md"), MARKDOWN_CONTENT_TYPE)

    assert [b.heading for b in blocks] == [
        "Wissensorganisation",
        "Beziehungen",
        "Beziehungen",
        "Beziehungen",
    ]
    # The "#" inside the fenced block must not be mistaken for a heading.
    assert "kein Heading" in blocks[2].text


def test_parse_markdown_without_headings_yields_paragraphs() -> None:
    blocks = parse_document(b"Erster Absatz.\n\nZweiter Absatz.", MARKDOWN_CONTENT_TYPE)

    assert [b.text for b in blocks] == ["Erster Absatz.", "Zweiter Absatz."]
    assert all(b.heading is None for b in blocks)


def test_parse_empty_document_yields_no_blocks() -> None:
    assert parse_document(b"   \n\n  ", MARKDOWN_CONTENT_TYPE) == []


def test_parse_unsupported_content_type_raises() -> None:
    with pytest.raises(ValueError, match="Content-Type"):
        parse_document(b"data", "application/zip")
