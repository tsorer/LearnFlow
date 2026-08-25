"""T-17: the two retrieval queries run against the real database.

`tests/test_retrieval.py` covers the fusion and the tsquery building, but it
drives `db.execute` through an AsyncMock — the SQL text itself is never parsed
by Postgres there. That leaves the core of the feature untested: a typo in the
`<=>` operator, in `to_tsvector('german', ...)` or in the two-step vector cast
would pass CI and only surface as a 503 in front of a user.

This module therefore executes DENSE_SQL and SPARSE_SQL for real. No provider
call is involved: `embed_texts` is stubbed with a handcrafted vector, so the
similarities are known in advance and the assertions can be exact.

Isolation is by `area`: retrieval filters on it, so a fixture area of its own
keeps the pilot corpus in the same database out of the results.

Precondition: a running stack (`make up`).
"""

import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.services import retrieval
from app.services.config import PipelineConfig

# Own area, so whatever else lives in the dev database cannot reach the results.
AREA = "e2e-retrieval"

CONFIG = PipelineConfig(
    similarity_threshold=0.35,
    min_retrieval_confidence=0.40,
    min_citation_coverage=0.50,
    # Stage 3 is out of scope here; the band is carried only because
    # PipelineConfig reads the whole config table in one go.
    self_check_band_low=0.50,
    self_check_band_high=0.75,
    retrieval_top_k=20,
    context_top_n=5,
    rrf_k=60,
)

# Two orthogonal unit vectors: cosine similarity 1.0 against itself, 0.0 against
# the other. That makes every score in the assertions below exact rather than
# approximate, which is the point of hand-building them.
NEAR_VECTOR = [1.0] + [0.0] * 1535
FAR_VECTOR = [0.0, 1.0] + [0.0] * 1534

# Only the far chunk carries the term, and it is the one the vector search puts
# last — so a sparse hit here can only come from the full-text query.
SPARSE_TERM = "Grundbedarf"


@pytest.fixture
async def corpus() -> AsyncIterator[uuid.UUID]:
    """A document with two chunks, removed again via the FK cascade."""
    conn = await asyncpg.connect(settings.asyncpg_dsn)
    document_id = uuid.uuid4()
    try:
        await conn.execute(
            "INSERT INTO documents (id, filename, content_type, content, status, area, "
            "chunk_count) VALUES ($1, $2, $3, $4, 'available', $5, 2)",
            document_id,
            "retrieval-e2e.md",
            "text/markdown",
            b"",
            AREA,
        )
        for index, (text, vector, page) in enumerate(
            [
                ("Semantisch nahe Passage ohne den Suchbegriff.", NEAR_VECTOR, 1),
                (f"Diese Passage nennt den {SPARSE_TERM} ausdruecklich.", FAR_VECTOR, 2),
            ]
        ):
            await conn.execute(
                "INSERT INTO chunks (id, document_id, content, chunk_index, page, embedding, tsv) "
                "VALUES ($1, $2, $3, $4, $5, $6::text::vector, to_tsvector('german', $3))",
                uuid.uuid4(),
                document_id,
                text,
                index,
                page,
                str(vector),
            )
        yield document_id
    finally:
        await conn.execute("DELETE FROM documents WHERE id = $1", document_id)
        await conn.close()


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    """A session per test, and a disposed pool afterwards.

    The engine in `app.database` is built at import time and its pooled
    connections belong to the event loop that first used them. pytest-asyncio
    hands every test a fresh loop, so a connection carried over from the
    previous test is closed underneath us — disposing here keeps the tests
    independent instead of ordering-dependent.
    """
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def stub_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    """No provider call: the query vector is the one the near chunk was stored with."""

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [NEAR_VECTOR]

    monkeypatch.setattr(retrieval, "embed_texts", fake_embed)


@pytest.mark.usefixtures("stub_embedding")
async def test_dense_and_sparse_run_against_postgres(
    corpus: uuid.UUID, db: AsyncSession
) -> None:
    outcome = await retrieval.retrieve(db, f"Was gilt zum {SPARSE_TERM}?", CONFIG, AREA)

    by_page = {hit.page: hit for hit in outcome.candidates}
    assert set(by_page) == {1, 2}, "beide Chunks muessen ueber die Fusion ankommen"

    # The cosine similarity comes out of DENSE_SQL's arithmetic, not out of
    # Python — these two values are what prove the operator and the cast work.
    assert by_page[1].score == pytest.approx(1.0, abs=1e-6)
    assert by_page[2].score == pytest.approx(0.0, abs=1e-6)

    # Dense returns both (there is no threshold in the WHERE clause, by design),
    # ordered by distance; sparse returns only the chunk carrying the term.
    assert outcome.dense_count == 2
    assert outcome.sparse_count == 1
    assert by_page[1].dense_rank == 1
    assert by_page[2].sparse_rank == 1

    # Found by both rankings beats found by one: page 2 is last for dense but
    # first for sparse, page 1 is first for dense and absent from sparse.
    assert outcome.context[0].page == 2


@pytest.mark.usefixtures("stub_embedding")
async def test_documents_outside_the_area_stay_invisible(
    corpus: uuid.UUID, db: AsyncSession
) -> None:
    """The area filter is the tenant boundary of the pilot — it must hold in SQL."""
    outcome = await retrieval.retrieve(db, f"Was gilt zum {SPARSE_TERM}?", CONFIG, "default")

    assert all(hit.filename != "retrieval-e2e.md" for hit in outcome.candidates)
