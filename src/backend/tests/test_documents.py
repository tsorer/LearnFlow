import io
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import User
from app.routers.documents import PILOT_AREA


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
        return await client.post("/documents", files=files, data={"area": PILOT_AREA})


@pytest.mark.parametrize("filename", ["notes.pdf", "report.docx", "readme.md"])
async def test_upload_success_returns_201(filename: str) -> None:
    db = make_db()
    r = await _post_upload(filename, b"fake content", db)

    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == filename
    assert body["status"] == "pending"
    assert body["area"] == PILOT_AREA
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


async def test_upload_unknown_area_returns_422() -> None:
    """A non-pilot area would create a document unreachable by list/get/delete."""
    db = make_db()
    app.dependency_overrides[get_current_user] = lambda: make_user("knowledge_owner")
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("notes.pdf", io.BytesIO(b"content"), "application/octet-stream")}
        r = await client.post("/documents", files=files, data={"area": "not-the-pilot-area"})

    assert r.status_code == 422
    db.add.assert_not_called()


def make_document(status: str = "processing", area: str = PILOT_AREA) -> object:
    from app.models.tables import Document

    return Document(
        id=uuid.uuid4(),
        filename="notes.pdf",
        content_type="application/pdf",
        content=b"x",
        status=status,
        area=area,
        uploaded_by=uuid.uuid4(),
        chunk_count=0,
        error_message=None,
        created_at=datetime.now(UTC),
    )


async def _get_document(
    document_id: uuid.UUID, db: AsyncMock, role: str | None = "knowledge_owner"
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


async def test_get_document_wrong_area_returns_404() -> None:
    document = make_document(area="other")
    db = make_db()
    db.get = AsyncMock(return_value=document)

    r = await _get_document(document.id, db)

    assert r.status_code == 404


async def test_get_document_wrong_role_returns_403() -> None:
    db = make_db()
    db.get = AsyncMock(return_value=make_document())

    r = await _get_document(uuid.uuid4(), db, role="learner")

    assert r.status_code == 403


async def test_get_document_no_auth_returns_401() -> None:
    db = make_db()
    r = await _get_document(uuid.uuid4(), db, role=None)
    assert r.status_code == 401


async def _list_documents(db: AsyncMock, role: str | None = "knowledge_owner") -> "object":
    if role is not None:
        app.dependency_overrides[get_current_user] = lambda: make_user(role)
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/documents")


def make_execute_result(documents: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = documents
    return result


async def test_list_documents_returns_documents() -> None:
    docs = [make_document(), make_document()]
    db = make_db()
    db.execute = AsyncMock(return_value=make_execute_result(docs))

    r = await _list_documents(db)

    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_list_documents_empty_returns_empty_list() -> None:
    db = make_db()
    db.execute = AsyncMock(return_value=make_execute_result([]))

    r = await _list_documents(db)

    assert r.status_code == 200
    assert r.json() == []


async def test_list_documents_query_filters_by_pilot_area_and_orders_newest_first() -> None:
    """A mocked db.execute ignores the statement it's called with — so the four
    other list tests above stay green even if `.where(...)`/`.order_by(...)` were
    deleted from list_documents. This test inspects the actual compiled SQL
    instead, so the area filter and ordering have real regression coverage."""
    db = make_db()
    db.execute = AsyncMock(return_value=make_execute_result([]))

    await _list_documents(db)

    stmt = db.execute.await_args[0][0]
    compiled = str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )
    assert f"documents.area = '{PILOT_AREA}'" in compiled
    assert "ORDER BY documents.created_at DESC" in compiled


async def test_list_documents_wrong_role_returns_403() -> None:
    db = make_db()
    r = await _list_documents(db, role="learner")
    assert r.status_code == 403


async def test_list_documents_no_auth_returns_401() -> None:
    db = make_db()
    r = await _list_documents(db, role=None)
    assert r.status_code == 401


async def _delete_document(
    document_id: uuid.UUID, db: AsyncMock, role: str | None = "knowledge_owner"
) -> "object":
    if role is not None:
        app.dependency_overrides[get_current_user] = lambda: make_user(role)
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.delete(f"/documents/{document_id}")


async def test_delete_document_returns_204() -> None:
    document = make_document()
    db = make_db()
    db.get = AsyncMock(return_value=document)
    db.delete = AsyncMock()

    r = await _delete_document(document.id, db)

    assert r.status_code == 204
    db.delete.assert_awaited_once_with(document)
    db.commit.assert_awaited_once()


async def test_delete_document_not_found_returns_404() -> None:
    db = make_db()
    db.get = AsyncMock(return_value=None)

    r = await _delete_document(uuid.uuid4(), db)

    assert r.status_code == 404


async def test_delete_document_wrong_area_returns_404() -> None:
    document = make_document(area="other")
    db = make_db()
    db.get = AsyncMock(return_value=document)

    r = await _delete_document(document.id, db)

    assert r.status_code == 404


async def test_delete_document_wrong_role_returns_403() -> None:
    db = make_db()
    db.get = AsyncMock(return_value=make_document())

    r = await _delete_document(uuid.uuid4(), db, role="learner")

    assert r.status_code == 403


async def test_delete_document_no_auth_returns_401() -> None:
    db = make_db()
    r = await _delete_document(uuid.uuid4(), db, role=None)
    assert r.status_code == 401
