"""T-14: DELETE /documents/{id} cascades to its chunks — against the real database.

The cascade is a foreign-key guarantee (`ondelete="CASCADE"` in migration 0003) —
no HTTP response can show whether it actually fired, only a query against the row
itself can. This connects to Postgres directly, the same way the worker does
(`app.config.settings.asyncpg_dsn`), instead of mocking it away like
`tests/test_documents.py` does.

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
# knowledge_owner will do — uploading and deleting is what needs the role.
#
# E2E_OWNER_* wins where it is set, so the suite also runs against a stack whose
# seed passwords have been replaced (Pilotstart-Checkliste 1.7).
_SEED_OWNER = next(u for u in USERS if u["role"] == "knowledge_owner")
EMAIL = os.environ.get("E2E_OWNER_EMAIL", _SEED_OWNER["email"])
PASSWORD = os.environ.get("E2E_OWNER_PASSWORD", _SEED_OWNER["password"])


@pytest.fixture(scope="module")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def token(client: httpx.Client) -> str:
    """The only login of this module — see test_login_flow.py's `login` fixture
    for why that matters (5 attempts/minute/IP, counter lives in the api process)."""
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


async def test_delete_document_cascades_to_chunks(
    client: httpx.Client, token: str, db_conn: asyncpg.Connection
) -> None:
    headers = {"Authorization": f"Bearer {token}"}

    # Unique per run: since T-15 an upload of a filename that already exists
    # replaces that document and answers 200, so a row left behind by an
    # aborted run would fail the assertion below.
    upload = client.post(
        "/api/documents",
        headers=headers,
        files={"file": (f"cascade-test-{uuid.uuid4()}.md", b"# cascade test", "text/markdown")},
        data={"area": "default"},
    )
    assert upload.status_code == 201, upload.text
    document_id = uuid.UUID(upload.json()["id"])

    # A chunk the worker would normally create (T-12/T-13 aren't implemented yet) —
    # inserted directly so there is something for the cascade to actually remove.
    await db_conn.execute(
        "INSERT INTO chunks (id, document_id, content, chunk_index) VALUES ($1, $2, $3, $4)",
        uuid.uuid4(),
        document_id,
        "test chunk",
        0,
    )
    chunks_before = await db_conn.fetchval(
        "SELECT count(*) FROM chunks WHERE document_id = $1", document_id
    )
    assert chunks_before == 1

    delete = client.delete(f"/api/documents/{document_id}", headers=headers)
    assert delete.status_code == 204, delete.text

    documents_after = await db_conn.fetchval(
        "SELECT count(*) FROM documents WHERE id = $1", document_id
    )
    chunks_after = await db_conn.fetchval(
        "SELECT count(*) FROM chunks WHERE document_id = $1", document_id
    )
    assert documents_after == 0
    assert chunks_after == 0
