"""T-15: a second upload of the same filename replaces the document — against
the real database.

What the HTTP response can show (status 200, unchanged id) is only half of the
ticket. That the chunks and embeddings of the replaced version are gone is a
property of the rows themselves, so this connects to Postgres directly, the same
way `test_documents_cascade.py` does.

Precondition: a running stack with seeded users (`make up && make seed`).
"""

import os
import uuid
from collections.abc import AsyncIterator, Iterator

import asyncpg
import httpx
import pytest

from app.config import settings
from seed_users import USERS

BASE_URL = os.environ.get("E2E_BASE_URL", "http://webapp")

# Taken from the seed script rather than copied: seed_users.py is where these
# dev credentials are defined, and a copy here would be a second plaintext
# password in the repository as well as a second place to keep in sync. Any
# knowledge_owner will do — uploading is what needs the role.
#
# E2E_OWNER_* wins where it is set, so the suite also runs against a stack whose
# seed passwords have been replaced (Pilotstart-Checkliste 1.7).
_SEED_OWNER = next(u for u in USERS if u["role"] == "knowledge_owner")
EMAIL = os.environ.get("E2E_OWNER_EMAIL", _SEED_OWNER["email"])
PASSWORD = os.environ.get("E2E_OWNER_PASSWORD", _SEED_OWNER["password"])

# Content of the chunk that stands in for the old version's index. Long enough
# to be unmistakably ours, so the assertion survives a worker run that writes
# real chunks for the same document in parallel.
OLD_CHUNK = "chunk of the version this test replaces"


@pytest.fixture(scope="module")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def token(client: httpx.Client) -> str:
    """The only login of this module. The rate limit keys on the client IP
    (5/minute), so every e2e module draws from the same budget no matter which
    user it logs in as — one login per module is what keeps the suite inside it.
    """
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 429:
        pytest.fail(
            "Rate limit exhausted (5 logins/minute/IP). The window outlives the "
            "test run: wait a minute or run `docker compose restart api`."
        )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


@pytest.fixture
async def db_conn() -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(settings.asyncpg_dsn)
    try:
        yield conn
    finally:
        await conn.close()


async def test_upload_of_the_same_filename_replaces_the_document(
    client: httpx.Client, token: str, db_conn: asyncpg.Connection
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    # Unique per run: a leftover row from an aborted run would otherwise turn
    # the first upload of the next run into a replacement.
    filename = f"replace-test-{uuid.uuid4()}.md"

    first = client.post(
        "/api/documents",
        headers=headers,
        files={"file": (filename, b"# erste fassung", "text/markdown")},
        data={"area": "default"},
    )
    assert first.status_code == 201, first.text
    document_id = uuid.UUID(first.json()["id"])

    try:
        # Stands in for the index of the first version. Written directly because
        # the worker's own run needs a reachable embedding provider, which this
        # test must not depend on.
        await db_conn.execute(
            "INSERT INTO chunks (id, document_id, content, chunk_index) VALUES ($1, $2, $3, $4)",
            uuid.uuid4(),
            document_id,
            OLD_CHUNK,
            0,
        )

        second = client.post(
            "/api/documents",
            headers=headers,
            files={"file": (filename, b"# zweite fassung", "text/markdown")},
            data={"area": "default"},
        )

        assert second.status_code == 200, second.text
        body = second.json()
        assert body["id"] == str(document_id)
        assert body["status"] == "pending"
        assert body["chunk_count"] == 0
        # The first upload's timestamp survives, the replacement gets its own.
        assert body["created_at"] == first.json()["created_at"]
        assert body["updated_at"] > body["created_at"]

        documents = await db_conn.fetchval(
            "SELECT count(*) FROM documents WHERE area = 'default' AND filename = $1", filename
        )
        content = await db_conn.fetchval(
            "SELECT content FROM documents WHERE id = $1", document_id
        )
        old_chunks = await db_conn.fetchval(
            "SELECT count(*) FROM chunks WHERE document_id = $1 AND content = $2",
            document_id,
            OLD_CHUNK,
        )

        assert documents == 1
        assert bytes(content) == b"# zweite fassung"
        assert old_chunks == 0
    finally:
        client.delete(f"/api/documents/{document_id}", headers=headers)


async def test_a_second_document_of_the_same_name_is_rejected_by_the_database(
    db_conn: asyncpg.Connection,
) -> None:
    """The route replaces instead of duplicating — migration 0013 makes that an
    invariant of the schema rather than a property of one code path. Written
    against the table directly: what is under test is the constraint, and going
    through the API would only ever exercise the replace branch.
    """
    filename = f"unique-test-{uuid.uuid4()}.md"
    rows = [uuid.uuid4(), uuid.uuid4()]

    async def insert(document_id: uuid.UUID) -> None:
        await db_conn.execute(
            "INSERT INTO documents (id, filename, content_type, content, status, area) "
            "VALUES ($1, $2, 'text/markdown', $3, 'pending', 'default')",
            document_id,
            filename,
            b"# fassung",
        )

    await insert(rows[0])
    try:
        with pytest.raises(asyncpg.exceptions.UniqueViolationError):
            await insert(rows[1])
    finally:
        await db_conn.execute("DELETE FROM documents WHERE id = ANY($1::uuid[])", rows)
