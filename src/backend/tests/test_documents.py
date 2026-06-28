import io
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import User


def make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()  # AsyncSession.add() is synchronous on the real session
    return db


def make_user(role: str) -> User:
    return User(
        id=uuid.uuid4(),
        email="owner@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


async def _post_upload(
    filename: str,
    content: bytes,
    db: AsyncMock,
    role: str | None = "knowledge_owner",
) -> "object":
    if role is not None:
        app.dependency_overrides[get_current_user] = lambda: make_user(role)
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": (filename, io.BytesIO(content), "application/octet-stream")}
        return await client.post("/documents", files=files, data={"area": "default"})


@pytest.mark.parametrize("filename", ["notes.pdf", "report.docx", "readme.md"])
async def test_upload_success_returns_201(filename: str) -> None:
    db = make_db()
    r = await _post_upload(filename, b"fake content", db)

    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == filename
    assert body["status"] == "pending"
    assert body["area"] == "default"
    assert body["chunk_count"] == 0
    assert body["error_message"] is None
    assert "id" in body
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


async def test_upload_wrong_role_returns_403() -> None:
    db = make_db()
    r = await _post_upload("notes.pdf", b"content", db, role="learner")
    assert r.status_code == 403


async def test_upload_no_auth_returns_401() -> None:
    db = make_db()
    r = await _post_upload("notes.pdf", b"content", db, role=None)
    assert r.status_code == 401


async def test_upload_unsupported_extension_returns_415() -> None:
    db = make_db()
    r = await _post_upload("malware.exe", b"content", db)
    assert r.status_code == 415


async def test_upload_oversized_file_returns_413() -> None:
    db = make_db()
    big_content = b"0" * (10 * 1024 * 1024 + 1)
    r = await _post_upload("big.pdf", big_content, db)
    assert r.status_code == 413


def make_document(status: str = "processing") -> object:
    from app.models.tables import Document

    return Document(
        id=uuid.uuid4(),
        filename="notes.pdf",
        content_type="application/pdf",
        content=b"x",
        status=status,
        area="default",
        uploaded_by=uuid.uuid4(),
        chunk_count=0,
        error_message=None,
        created_at=datetime.now(UTC),
    )


async def _get_document(
    document_id: uuid.UUID, db: AsyncMock, role: str | None = "learner"
) -> "object":
    if role is not None:
        app.dependency_overrides[get_current_user] = lambda: make_user(role)
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(f"/documents/{document_id}")


async def test_get_document_returns_200_with_status() -> None:
    document = make_document(status="processing")
    db = make_db()
    db.get = AsyncMock(return_value=document)

    r = await _get_document(document.id, db)

    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(document.id)
    assert body["status"] == "processing"


async def test_get_document_not_found_returns_404() -> None:
    db = make_db()
    db.get = AsyncMock(return_value=None)

    r = await _get_document(uuid.uuid4(), db)

    assert r.status_code == 404


async def test_get_document_no_auth_returns_401() -> None:
    db = make_db()
    r = await _get_document(uuid.uuid4(), db, role=None)
    assert r.status_code == 401
