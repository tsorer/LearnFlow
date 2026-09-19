"""T-57: the snapshot step of the calibration sweep (ADR-009 calibration loop).

Everything downstream of a question's raw retrieval rows is a pure function
(`fuse()`, the gate/confidence functions in `app/services/confidence.py`) — the only parts
of a retrieval that actually cost a round-trip are the question embedding and the two SQL
fetches. This module runs those once per question, for *all* 80 dataset questions (not just
the 45 `in_corpus` ones: Schicht A2 needs the pre-generation gate outcome for
`out_of_corpus`/`adversarial` questions too, see `eval/calibrate_grid.py`), at a generous
`top_k` (`SNAPSHOT_TOP_K`) so every candidate `retrieval_top_k` the grid sweeps stays within
it. Everything after that — different `(retrieval_top_k, rrf_k, context_top_n)` — is then
`fetch_rows()`/`fuse()` replayed against rows already in memory, no second query.

Deliberately without chunk content: the snapshot is evaluated against `expected_source`
(filename + page), which the retrieval rows already carry, so Schicht A never needs the
chunk text. Schicht B (`eval/calibrate_run.py`) fetches content once per unique context it
actually generates from, by `chunk_id` — a few hundred chunks at most, not the ~9 MB a
content-bearing snapshot of every candidate for every question would be.

A snapshot is worthless once the index or the embedding model has moved on: the rows it
holds no longer describe what a live query would retrieve. `index_hash` makes that
detectable instead of silently measuring a stale pipeline (`verify_index_hash` below).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import Config, Document, DocumentStatus
from app.routers.documents import PILOT_AREA
from app.services.embedding import embed_texts
from app.services.retrieval import DENSE_SQL, SPARSE_SQL, fetch_rows, to_tsquery_terms
from eval.gold_dataset import (
    load_adversarial_questions,
    load_in_corpus_questions,
    load_out_of_corpus_questions,
)

#: Comfortably above every `retrieval_top_k` candidate in the grid (`eval/calibrate_grid.py`
#: caps its own candidates at this value) — raising a grid candidate above it would silently
#: under-count that combination's dense/sparse pool instead of failing loudly, so
#: `eval/calibrate_grid.py` asserts its own top_k values against this constant.
SNAPSHOT_TOP_K = 100

CONFIG_HASH_KEYS = ("chunk_size", "chunk_overlap")


@dataclasses.dataclass(frozen=True)
class SnapshotRow:
    """One candidate row exactly as the DENSE_SQL/SPARSE_SQL columns deliver it."""

    chunk_id: str
    document_id: str
    filename: str
    page: int | None
    heading: str | None
    score: float


@dataclasses.dataclass(frozen=True)
class QuestionSnapshot:
    """The frozen retrieval for one dataset question."""

    id: str
    category: str
    #: None for `out_of_corpus` — no corpus is the point of that category.
    corpus: str | None
    question: str
    dense: list[SnapshotRow]
    sparse: list[SnapshotRow]


@dataclasses.dataclass(frozen=True)
class Snapshot:
    created_at: str
    embedding_model: str
    index_hash: str
    top_k: int
    questions: list[QuestionSnapshot]


class SnapshotStaleError(Exception):
    """The snapshot's `index_hash` no longer matches the live index (AC 1).

    Raised instead of silently replaying a grid against rows that no longer describe what
    the live pipeline would retrieve — a re-indexed or re-chunked corpus, or a changed
    embedding model, invalidates every downstream number.
    """


async def compute_index_hash(db: AsyncSession) -> str:
    """`sha256` over the available documents' `(id, filename, chunk_count)` plus
    `chunk_size`/`chunk_overlap` and the embedding model (AC 1).

    `chunk_count` stands in for hashing every chunk: it already changes whenever chunking
    or re-indexing changes what a document contributes, and reading it costs nothing extra
    (`documents.chunk_count`, T-43) — a full chunk-content hash would cost a second query
    doing exactly what fetching chunks in Schicht B already does, for no more sensitivity.
    """
    documents = await db.execute(
        select(Document.id, Document.filename, Document.chunk_count)
        .where(Document.status == DocumentStatus.available, Document.area == PILOT_AREA)
        .order_by(Document.id)
    )
    config_rows = await db.execute(
        select(Config.key, Config.value).where(Config.key.in_(CONFIG_HASH_KEYS))
    )
    config_values: dict[str, str] = {key: value for key, value in config_rows.all()}

    payload = {
        "documents": sorted(
            (str(row.id), row.filename, row.chunk_count) for row in documents.all()
        ),
        "chunk_size": config_values.get("chunk_size"),
        "chunk_overlap": config_values.get("chunk_overlap"),
        "embedding_model": settings.embed_model,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def verify_index_hash(snapshot: Snapshot, current_hash: str) -> None:
    """Raises `SnapshotStaleError` when the snapshot no longer matches the live index."""
    if snapshot.index_hash != current_hash:
        raise SnapshotStaleError(
            f"Snapshot-Indexstand ({snapshot.index_hash}) passt nicht zum aktuellen "
            f"Indexstand ({current_hash}) — Korpus oder Chunking-Parameter oder "
            f"Embedding-Modell haben sich seit dem Snapshot geändert. Snapshot neu "
            "erzeugen (`make calibrate`), statt eine andere Pipeline zu messen."
        )


def _dataset_questions() -> list[tuple[str, str, str | None, str]]:
    """`(id, category, corpus, question)` for all 80 questions, all three categories."""
    rows: list[tuple[str, str, str | None, str]] = []
    for in_corpus_q in load_in_corpus_questions():
        rows.append((in_corpus_q.id, "in_corpus", in_corpus_q.corpus, in_corpus_q.question))
    for adversarial_q in load_adversarial_questions():
        rows.append(
            (adversarial_q.id, "adversarial", adversarial_q.corpus, adversarial_q.question)
        )
    for out_of_corpus_q in load_out_of_corpus_questions():
        rows.append((out_of_corpus_q.id, "out_of_corpus", None, out_of_corpus_q.question))
    return rows


def _to_rows(raw: Sequence[Mapping[str, Any]]) -> list[SnapshotRow]:
    return [
        SnapshotRow(
            chunk_id=str(row["chunk_id"]),
            document_id=str(row["document_id"]),
            filename=row["filename"],
            page=row["page"],
            heading=row["heading"],
            score=float(row["score"]),
        )
        for row in raw
    ]


async def build_snapshot(db: AsyncSession, *, top_k: int = SNAPSHOT_TOP_K) -> Snapshot:
    """Embed every dataset question once, fetch dense/sparse rows once each (AC 1).

    Sequential per question and per search, like `retrieve()`: one `AsyncSession` holds one
    asyncpg connection, which forbids concurrent operations on it.
    """
    index_hash = await compute_index_hash(db)
    questions = _dataset_questions()
    embeddings = await embed_texts([question for *_rest, question in questions])

    snapshots: list[QuestionSnapshot] = []
    for (qid, category, corpus, question_text), embedding in zip(
        questions, embeddings, strict=True
    ):
        params: dict[str, Any] = {
            "embedding": json.dumps(embedding),
            "area": PILOT_AREA,
            "top_k": top_k,
            "status": DocumentStatus.available,
        }
        dense = await fetch_rows(db, DENSE_SQL, params)
        tsquery = to_tsquery_terms(question_text)
        sparse = (
            await fetch_rows(db, SPARSE_SQL, {**params, "tsquery": tsquery}) if tsquery else []
        )
        snapshots.append(
            QuestionSnapshot(
                id=qid,
                category=category,
                corpus=corpus,
                question=question_text,
                dense=_to_rows(dense),
                sparse=_to_rows(sparse),
            )
        )

    return Snapshot(
        created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ"),
        embedding_model=settings.embed_model,
        index_hash=index_hash,
        top_k=top_k,
        questions=snapshots,
    )


def write_snapshot(snapshot: Snapshot, out_dir: pathlib.Path) -> pathlib.Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "snapshot.json"
    path.write_text(
        json.dumps(dataclasses.asdict(snapshot), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_snapshot(path: pathlib.Path) -> Snapshot:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Snapshot(
        created_at=raw["created_at"],
        embedding_model=raw["embedding_model"],
        index_hash=raw["index_hash"],
        top_k=raw["top_k"],
        questions=[
            QuestionSnapshot(
                id=q["id"],
                category=q["category"],
                corpus=q["corpus"],
                question=q["question"],
                dense=[SnapshotRow(**row) for row in q["dense"]],
                sparse=[SnapshotRow(**row) for row in q["sparse"]],
            )
            for q in raw["questions"]
        ],
    )


def snapshot_row_as_hit_dict(row: SnapshotRow) -> dict[str, Any]:
    """`SnapshotRow` as the mapping shape `fuse()` expects (`chunk_id` as `uuid.UUID`).

    `fuse()` keys rows by `chunk_id` and reads `document_id`/`content`/`page`/`heading`/
    `score` off them (`app/services/retrieval.py`); the snapshot carries no `content` — an
    empty string stands in, since Schicht A never reads it (only `expected_source` matching
    on filename/page), and Schicht B replaces it with the real content it fetches by
    `chunk_id` before generation.
    """
    return {
        "chunk_id": uuid.UUID(row.chunk_id),
        "document_id": uuid.UUID(row.document_id),
        "content": "",
        "page": row.page,
        "heading": row.heading,
        "filename": row.filename,
        "score": row.score,
    }
