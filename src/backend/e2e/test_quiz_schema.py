"""T-34: the quiz_questions schema, checked against the real database.

Three of the guarantees this ticket rests on exist only in Postgres and are
invisible to every mocked test: the two CHECK constraints, and the
`ON DELETE SET NULL` that lets a question outlive the chunk it was generated
from. `tests/test_quiz_endpoint.py` can show what the endpoint hands the
session; only a query can show what the database does with it.

Precondition: a running stack with migrations applied (`alembic upgrade head`).
"""

import json
import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest

from app.config import settings

OPTIONS = ["Hochrisiko-Systeme", "Steuerrecht", "Baurecht", "Seerecht"]


@pytest.fixture
async def db_conn() -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(settings.asyncpg_dsn)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def document(db_conn: asyncpg.Connection) -> AsyncIterator[uuid.UUID]:
    """A document with one chunk, removed again afterwards.

    Deleting the document is enough: chunks and questions both hang off it with
    ON DELETE CASCADE, so the cleanup exercises that path as a side effect.
    """
    document_id = uuid.uuid4()
    await db_conn.execute(
        "INSERT INTO documents (id, filename, content_type, content, status, area) "
        "VALUES ($1, $2, 'text/markdown', $3, 'available', $4)",
        document_id,
        f"quiz-schema-{document_id}.md",
        b"# quiz schema test",
        "default",
    )
    try:
        yield document_id
    finally:
        await db_conn.execute("DELETE FROM documents WHERE id = $1", document_id)


async def insert_chunk(conn: asyncpg.Connection, document_id: uuid.UUID) -> uuid.UUID:
    chunk_id = uuid.uuid4()
    await conn.execute(
        "INSERT INTO chunks (id, document_id, content, chunk_index) VALUES ($1, $2, $3, 0)",
        chunk_id,
        document_id,
        "Der AI Act regelt Hochrisiko-Systeme.",
    )
    return chunk_id


async def insert_question(
    conn: asyncpg.Connection,
    document_id: uuid.UUID,
    chunk_id: uuid.UUID | None = None,
    status: str = "pending",
    options: list[str] | None = None,
) -> uuid.UUID:
    question_id = uuid.uuid4()
    await conn.execute(
        "INSERT INTO quiz_questions "
        "(id, document_id, chunk_id, question, options, correct_answer, explanation, "
        " source_excerpt, status) "
        "VALUES ($1, $2, $3, $4, $5::jsonb, 'A', $6, $7, $8)",
        question_id,
        document_id,
        chunk_id,
        "Was regelt der AI Act?",
        json.dumps(OPTIONS if options is None else options),
        "Der Abschnitt nennt Hochrisiko-Systeme.",
        "Der AI Act regelt Hochrisiko-Systeme.",
        status,
    )
    return question_id


async def test_status_defaults_to_pending(
    db_conn: asyncpg.Connection, document: uuid.UUID
) -> None:
    """Fail-closed by construction: a row that reaches the table without anyone
    naming a status is not an approved one (ADR-008)."""
    question_id = uuid.uuid4()
    await db_conn.execute(
        "INSERT INTO quiz_questions "
        "(id, document_id, question, options, correct_answer, explanation, source_excerpt) "
        "VALUES ($1, $2, 'Frage?', $3::jsonb, 'A', 'Weil.', 'Passage.')",
        question_id,
        document,
        json.dumps(OPTIONS),
    )

    status = await db_conn.fetchval(
        "SELECT status FROM quiz_questions WHERE id = $1", question_id
    )
    assert status == "pending"


async def test_an_unknown_status_is_rejected(
    db_conn: asyncpg.Connection, document: uuid.UUID
) -> None:
    """The three values of T-34 are a fact about the database, not a convention
    in the application: this endpoint is not the only writer — T-35 edits these
    rows, and psql reaches them too."""
    with pytest.raises(asyncpg.CheckViolationError):
        await insert_question(db_conn, document, status="freigegeben")


@pytest.mark.parametrize("options", [OPTIONS[:3], [*OPTIONS, "Fuenfte"]])
async def test_a_question_without_four_options_is_rejected(
    db_conn: asyncpg.Connection, document: uuid.UUID, options: list[str]
) -> None:
    """Four options is an acceptance criterion, not a rendering detail: the
    `correct_answer` labels A to D index exactly this array."""
    with pytest.raises(asyncpg.CheckViolationError):
        await insert_question(db_conn, document, options=options)


async def test_deleting_the_chunk_keeps_the_question_and_clears_the_reference(
    db_conn: asyncpg.Connection, document: uuid.UUID
) -> None:
    """The decision of T-33 (#40) as the database enforces it.

    Replacing a document deletes the chunks of the old version. The questions
    survive that — and `chunk_id IS NULL` is what marks them afterwards as
    "generated from a version that no longer exists", which is why the excerpt
    is stored alongside the reference.
    """
    chunk_id = await insert_chunk(db_conn, document)
    question_id = await insert_question(db_conn, document, chunk_id=chunk_id)

    await db_conn.execute("DELETE FROM chunks WHERE id = $1", chunk_id)

    row = await db_conn.fetchrow(
        "SELECT chunk_id, source_excerpt FROM quiz_questions WHERE id = $1", question_id
    )
    assert row is not None, "die Frage darf die Ersetzung des Dokuments überleben"
    assert row["chunk_id"] is None
    assert row["source_excerpt"] == "Der AI Act regelt Hochrisiko-Systeme."


async def test_deleting_the_document_removes_its_questions(
    db_conn: asyncpg.Connection, document: uuid.UUID
) -> None:
    """Unlike the chunk, the document takes its questions with it: without the
    document there is no area, no corpus and nothing left to review."""
    question_id = await insert_question(db_conn, document)

    await db_conn.execute("DELETE FROM documents WHERE id = $1", document)

    assert await db_conn.fetchval(
        "SELECT count(*) FROM quiz_questions WHERE id = $1", question_id
    ) == 0
