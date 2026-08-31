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


def make_db(existing: object | None = None) -> AsyncMock:
    """A session whose queries return no rows unless a test says otherwise.

    `existing` is what the filename lookup of the upload finds (T-15): None for
    a first upload, a Document for one that replaces it. Without an explicit
    result a bare AsyncMock would answer `scalar_one_or_none()` with a truthy
    Mock — every upload test would take the replace branch.
    """
    db = AsyncMock()
    db.add = MagicMock()  # AsyncSession.add() is synchronous on the real session
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=result)
    # get_document resolves uploaded_by to an e-mail via db.scalar(); default to
    # None (deleted account) so tests that don't care produce a valid response.
    db.scalar = AsyncMock(return_value=None)
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
    # Nothing has replaced this document yet, so both timestamps are the upload.
    assert body["updated_at"] == body["created_at"]
    # The uploader of a fresh document is the authenticated user (#92).
    assert body["uploaded_by"] == "owner@example.com"
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


async def test_upload_unknown_area_returns_400() -> None:
    """A non-pilot area would create a document unreachable by list/get/delete.

    400, not 422: FastAPI's own request validation (e.g. a missing file) already
    owns 422 with a different body shape (an array, not a string) — this business
    rule needs a status of its own to keep the spec's `422 -> Error` unambiguous.
    """
    db = make_db()
    app.dependency_overrides[get_current_user] = lambda: make_user("knowledge_owner")
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("notes.pdf", io.BytesIO(b"content"), "application/octet-stream")}
        r = await client.post("/documents", files=files, data={"area": "not-the-pilot-area"})

    assert r.status_code == 400
    db.add.assert_not_called()


def statements(db: AsyncMock) -> list[tuple[str, dict]]:
    """SQL and bound parameters of everything the route executed.

    A mocked session answers every statement the same way, so the tests that
    only read the response body stay green even if the filename filter or the
    chunk deletion were dropped. These assertions look at the statements
    themselves.
    """
    rendered = []
    for call in db.execute.await_args_list:
        compiled = call.args[0].compile(dialect=postgresql.dialect())
        params = dict(compiled.params)
        # text() statements carry their values in the second argument, not in
        # the statement itself.
        if len(call.args) > 1 and isinstance(call.args[1], dict):
            params.update(call.args[1])
        rendered.append((str(compiled), params))
    return rendered


def only(db: AsyncMock, fragment: str) -> tuple[str, dict]:
    matches = [(sql, params) for sql, params in statements(db) if fragment in sql]
    assert len(matches) == 1, f"expected exactly one {fragment!r}, got {len(matches)}"
    return matches[0]


async def test_upload_looks_the_filename_up_in_the_pilot_area() -> None:
    db = make_db()

    await _post_upload("notes.pdf", b"content", db)

    sql, params = only(db, "FROM documents")
    assert "documents.filename = " in sql
    assert "documents.area = " in sql
    assert {"notes.pdf", PILOT_AREA} <= set(params.values())
    # Serialises two uploads of the same name; without it both would find no
    # predecessor and create a document each.
    assert "FOR UPDATE" in sql


async def test_upload_existing_filename_replaces_and_returns_200() -> None:
    existing = make_document(status="failed")
    existing.chunk_count = 7
    existing.error_message = "Verarbeitung fehlgeschlagen"
    existing.validated_at = datetime.now(UTC)
    db = make_db(existing=existing)

    r = await _post_upload(existing.filename, b"zweite fassung", db)

    assert r.status_code == 200
    body = r.json()
    # Same row, same id: the frontend polls it and answers reference it.
    assert body["id"] == str(existing.id)
    assert body["status"] == "pending"
    assert body["chunk_count"] == 0
    assert body["error_message"] is None
    # created_at stays with the first upload, updated_at moves to this one —
    # that pair is how the list tells a replaced document from a new one.
    assert datetime.fromisoformat(body["created_at"]) == existing.created_at
    assert datetime.fromisoformat(body["updated_at"]) > existing.created_at
    # New bytes void every run still indexing the old ones (T-43): the token
    # moves, so their publish fails the guard in worker/main.py. The attempt
    # budget starts over — a new version deserves fresh attempts.
    assert existing.index_version == 2
    assert existing.index_attempts == 0
    assert existing.content == b"zweite fassung"
    # The replacement has not been validated, whatever its predecessor reached.
    assert existing.validated_at is None
    # A replacement records the replacing user as the current uploader (#92).
    assert body["uploaded_by"] == "owner@example.com"
    db.add.assert_not_called()
    db.commit.assert_awaited_once()


async def test_upload_replacement_deletes_the_previous_chunks() -> None:
    """The acceptance criterion the response body cannot show: the embeddings of
    the replaced version leave the database with the upload, not with the
    re-indexing run that may still fail."""
    existing = make_document(status="available")
    db = make_db(existing=existing)

    await _post_upload(existing.filename, b"zweite fassung", db)

    _, params = only(db, "DELETE FROM chunks")
    assert existing.id in params.values()


async def test_upload_replacement_sends_approved_questions_back_to_review() -> None:
    """The decision of T-33 (#40), and the response body cannot show it either.

    Deleting the questions would discard Stefan's review silently; leaving them
    approved would keep questions in the learners' pool that were checked
    against a text nobody can read any more. So the approval goes and the
    question stays — including its approval timestamp, which would otherwise
    claim a verdict that no longer holds (US-07).
    """
    existing = make_document(status="available")
    db = make_db(existing=existing)

    await _post_upload(existing.filename, b"zweite fassung", db)

    sql, params = only(db, "UPDATE quiz_questions")
    assert "quiz_questions.status = " in sql
    assert {"pending", "approved", existing.id} <= set(params.values())
    assert None in params.values()  # approved_at


async def test_upload_of_a_new_filename_touches_no_questions() -> None:
    """Nothing has been generated from a document that did not exist."""
    db = make_db()

    await _post_upload("notes.pdf", b"content", db)

    assert not [sql for sql, _ in statements(db) if "UPDATE quiz_questions" in sql]


async def test_upload_of_a_new_filename_deletes_no_chunks() -> None:
    db = make_db()

    r = await _post_upload("notes.pdf", b"content", db)

    assert r.status_code == 201
    assert not [sql for sql, _ in statements(db) if "DELETE FROM chunks" in sql]


async def test_upload_replacement_re_indexes_the_existing_document() -> None:
    existing = make_document(status="available")
    db = make_db(existing=existing)

    await _post_upload(existing.filename, b"zweite fassung", db)

    _, params = only(db, "INSERT INTO pgqueuer")
    assert str(existing.id) in params["payload"].decode()


def make_document(status: str = "processing", area: str = PILOT_AREA) -> object:
    from app.models.tables import Document

    # A document uploaded once and never replaced: both timestamps are the same
    # moment, as they are on a fresh insert.
    uploaded_at = datetime.now(UTC)
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
        created_at=uploaded_at,
        updated_at=uploaded_at,
        # The first version, its attempts untouched — what a fresh insert sets.
        index_version=1,
        index_attempts=0,
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
    # uploaded_by is a UUID on the row; the router resolves it to an e-mail.
    db.scalar = AsyncMock(return_value="owner@example.com")

    r = await _get_document(document.id, db)

    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(document.id)
    assert body["status"] == "processing"
    assert body["uploaded_by"] == "owner@example.com"


async def test_get_document_without_uploader_returns_null() -> None:
    # A document whose uploader account was deleted (FK ON DELETE SET NULL): the
    # router must not run a lookup for a null id and must serve uploaded_by null.
    document = make_document(status="available")
    document.uploaded_by = None
    db = make_db()
    db.get = AsyncMock(return_value=document)

    r = await _get_document(document.id, db)

    assert r.status_code == 200
    assert r.json()["uploaded_by"] is None
    db.scalar.assert_not_awaited()


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


def make_execute_result(
    documents: list[object], uploader_email: str | None = "owner@example.com"
) -> MagicMock:
    # list_documents selects (Document, User.email) and iterates result.all(),
    # so each row is a (document, email) tuple — not result.scalars().all().
    result = MagicMock()
    result.all.return_value = [(d, uploader_email) for d in documents]
    return result


async def test_list_documents_returns_documents() -> None:
    docs = [make_document(), make_document()]
    db = make_db()
    db.execute = AsyncMock(return_value=make_execute_result(docs))

    r = await _list_documents(db)

    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_list_documents_includes_uploader_email() -> None:
    db = make_db()
    db.execute = AsyncMock(
        return_value=make_execute_result([make_document()], uploader_email="frank@example.com")
    )

    r = await _list_documents(db)

    assert r.status_code == 200
    assert r.json()[0]["uploaded_by"] == "frank@example.com"


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
