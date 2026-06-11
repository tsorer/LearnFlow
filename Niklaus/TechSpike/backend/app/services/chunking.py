"""Structure-aware chunker — headings preserved as context per ADR-007.

Chunk size and overlap are read from the config table at runtime (defaults from settings).
"""

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    content: str
    chunk_index: int
    page: int | None = None
    heading: str | None = None


def _approx_tokens(text: str) -> int:
    # rough estimate: 4 chars ≈ 1 token
    return len(text) // 4


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    page: int | None = None,
    heading: str | None = None,
) -> list[Chunk]:
    """Split text into overlapping chunks, preserving heading context."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0
    idx = 0

    for para in paragraphs:
        # detect headings (lines starting with # or ALL CAPS short line)
        is_heading = para.startswith("#") or (len(para) < 80 and para.isupper())
        if is_heading:
            heading = para.lstrip("#").strip()

        para_tokens = _approx_tokens(para)

        if current_tokens + para_tokens > chunk_size and current:
            chunk_text_joined = "\n\n".join(current)
            if heading:
                chunk_text_joined = f"[{heading}]\n\n{chunk_text_joined}"
            chunks.append(Chunk(content=chunk_text_joined, chunk_index=idx, page=page, heading=heading))
            idx += 1

            # keep overlap: last paragraph(s) summing to ~overlap tokens
            overlap_paras: list[str] = []
            overlap_tokens = 0
            for p in reversed(current):
                t = _approx_tokens(p)
                if overlap_tokens + t <= overlap:
                    overlap_paras.insert(0, p)
                    overlap_tokens += t
                else:
                    break
            current = overlap_paras
            current_tokens = overlap_tokens

        current.append(para)
        current_tokens += para_tokens

    if current:
        chunk_text_joined = "\n\n".join(current)
        if heading:
            chunk_text_joined = f"[{heading}]\n\n{chunk_text_joined}"
        chunks.append(Chunk(content=chunk_text_joined, chunk_index=idx, page=page, heading=heading))

    return chunks


def extract_pdf_chunks(content: bytes, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    from pypdf import PdfReader
    import io

    reader = PdfReader(io.BytesIO(content))
    all_chunks: list[Chunk] = []
    global_idx = 0

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        page_chunks = chunk_text(text, chunk_size, overlap, page=page_num)
        for c in page_chunks:
            c.chunk_index = global_idx
            global_idx += 1
        all_chunks.extend(page_chunks)

    return all_chunks


def extract_docx_chunks(content: bytes, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    from docx import Document as DocxDocument
    import io

    doc = DocxDocument(io.BytesIO(content))
    current_heading: str | None = None
    full_text_parts: list[tuple[str, str | None]] = []

    for para in doc.paragraphs:
        if not para.text.strip():
            continue
        if para.style and para.style.name and para.style.name.startswith("Heading"):
            current_heading = para.text.strip()
        full_text_parts.append((para.text.strip(), current_heading))

    all_chunks: list[Chunk] = []
    global_idx = 0
    text_block = "\n\n".join(p for p, _ in full_text_parts)
    chunks = chunk_text(text_block, chunk_size, overlap)
    for c in chunks:
        c.chunk_index = global_idx
        global_idx += 1
    all_chunks.extend(chunks)

    return all_chunks


def extract_md_chunks(content: bytes, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    text = content.decode("utf-8", errors="replace")
    return chunk_text(text, chunk_size, overlap)
