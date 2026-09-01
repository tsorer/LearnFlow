"""The read, write and sample endpoints around the human gate (T-49).

Two kinds of test, on purpose. The rules that decide what a role sees and what
an edit does to a verdict are pure functions, and they are tested as such: no
HTTP, no session, one rule per assertion. The endpoint tests around them check
the wiring only — status codes, the shape of the page, and that the role
actually reaches the SQL. Auth is bypassed through `app.dependency_overrides`
here; the real token path is covered once, for every endpoint, in test_rbac.py.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.tables import QuizQuestion, QuizQuestionStatus, User
from app.routers.quiz import QUIZ_LENGTH, QuizQuestionUpdate, apply_update, visible_statuses

NOW = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
YESTERDAY = NOW - timedelta(days=1)


def make_user(role: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role}@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        created_at=NOW,
    )


def make_row(
    status: QuizQuestionStatus = QuizQuestionStatus.pending,
    approved_at: datetime | None = None,
) -> QuizQuestion:
    return QuizQuestion(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_id=uuid.uuid4(),
        question="Was regelt der AI Act?",
        options=["Hochrisiko-Systeme", "Steuerrecht", "Baurecht", "Seerecht"],
        correct_answer="A",
        explanation="Der Abschnitt nennt Hochrisiko-Systeme.",
        source_excerpt="Der AI Act regelt Hochrisiko-Systeme.",
        status=status.value,
        created_at=NOW - timedelta(minutes=5),
        approved_at=approved_at,
    )


def override(user: User, db: AsyncMock) -> None:
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db


def make_list_db(rows: list[QuizQuestion], total: int | None = None) -> AsyncMock:
    """Session answering the two queries of the GET: the count, then the page."""
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=len(rows) if total is None else total)
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=result)
    return db


def make_patch_db(row: QuizQuestion | None) -> AsyncMock:
    db = AsyncMock()
    db.get = AsyncMock(return_value=row)
    return db


def compiled(call: Any) -> str:
    """The SQL a mocked session was handed, as text."""
    return str(call.args[0].compile(compile_kwargs={"literal_binds": True}))


def assert_validation_error_body(payload: Any) -> None:
    """A 422 out of these endpoints must look like the `ValidationError` schema.

    Both endpoints let FastAPI reject the request, so `detail` is a *list* of
    single errors and not the string of the `Error` schema. Asserted on the body
    and not just on the status code, because openapi.yaml has to name the right
    one of the two: the frontend types are generated from it, and a board typed
    for `{detail: string}` renders the wrong thing on every rejected edit — the
    `ValidationError` schema says as much in its own description.
    """
    detail = payload["detail"]
    assert isinstance(detail, list), detail
    assert all({"loc", "msg", "type"} <= set(error) for error in detail), detail


# ---- visible_statuses: who sees what (no DB, no HTTP) ---------------------


def test_reviewer_without_filter_sees_all_three() -> None:
    assert visible_statuses("knowledge_owner", None) == set(QuizQuestionStatus)


def test_admin_sees_all_three() -> None:
    assert visible_statuses("admin", None) == set(QuizQuestionStatus)


def test_reviewer_with_filter_sees_exactly_that_status() -> None:
    assert visible_statuses("knowledge_owner", QuizQuestionStatus.rejected) == {
        QuizQuestionStatus.rejected
    }


def test_learner_without_filter_sees_only_approved() -> None:
    assert visible_statuses("learner", None) == {QuizQuestionStatus.approved}


def test_learner_asking_for_pending_sees_nothing() -> None:
    """The filter narrows the permitted set and never widens it — so this ends
    as an empty page, not as a 403 (status code checked further down)."""
    assert visible_statuses("learner", QuizQuestionStatus.pending) == set()


def test_unknown_role_is_treated_as_a_learner() -> None:
    """Fail-closed: a role added later without a thought spared for this list
    must not inherit the reviewer's view of unapproved questions."""
    assert visible_statuses("auditor", None) == {QuizQuestionStatus.approved}


# ---- apply_update: the verdict rules (no DB, no HTTP) ---------------------


def test_approving_stamps_approved_at() -> None:
    row = make_row()
    apply_update(row, QuizQuestionUpdate(status=QuizQuestionStatus.approved), NOW)
    assert row.status == "approved"
    assert row.approved_at == NOW


@pytest.mark.parametrize("status", [QuizQuestionStatus.pending, QuizQuestionStatus.rejected])
def test_any_other_status_clears_approved_at(status: QuizQuestionStatus) -> None:
    row = make_row(QuizQuestionStatus.approved, approved_at=YESTERDAY)
    apply_update(row, QuizQuestionUpdate(status=status), NOW)
    assert row.status == status.value
    assert row.approved_at is None


def test_editing_an_approved_question_sends_it_back_to_pending() -> None:
    """ADR-008: an approval on file must not end up covering a text that nobody
    approved in that form."""
    row = make_row(QuizQuestionStatus.approved, approved_at=YESTERDAY)
    apply_update(row, QuizQuestionUpdate(question="Was genau regelt der AI Act?"), NOW)
    assert row.question == "Was genau regelt der AI Act?"
    assert row.status == "pending"
    assert row.approved_at is None


def test_editing_and_approving_in_one_request_stays_approved() -> None:
    row = make_row(QuizQuestionStatus.approved, approved_at=YESTERDAY)
    apply_update(
        row,
        QuizQuestionUpdate(
            question="Was genau regelt der AI Act?", status=QuizQuestionStatus.approved
        ),
        NOW,
    )
    assert row.status == "approved"
    assert row.approved_at == NOW


def test_resending_approved_on_an_unchanged_question_keeps_the_original_stamp() -> None:
    """A save that changes nothing is not a second approval.

    The board round-trips `status` alongside the content fields, so without
    this an approved question would take the date of the last time anyone
    opened and saved it — while US-07 asks for the moment of the approval.
    Same rule as for the content fields, which is where this one was missing.
    """
    row = make_row(QuizQuestionStatus.approved, approved_at=YESTERDAY)
    apply_update(row, QuizQuestionUpdate(status=QuizQuestionStatus.approved), NOW)
    assert row.status == "approved"
    assert row.approved_at == YESTERDAY


def test_resending_approved_together_with_the_identical_text_keeps_the_stamp() -> None:
    """The full round-trip a board actually sends: status plus all four
    content fields, none of them changed."""
    row = make_row(QuizQuestionStatus.approved, approved_at=YESTERDAY)
    apply_update(
        row,
        QuizQuestionUpdate(
            status=QuizQuestionStatus.approved,
            question=row.question,
            options=list(row.options),
            correct_answer=row.correct_answer,
            explanation=row.explanation,
        ),
        NOW,
    )
    assert row.approved_at == YESTERDAY


def test_approving_again_after_a_withdrawal_stamps_anew() -> None:
    """Not the same case: the approval really is new, so its moment is now."""
    row = make_row(QuizQuestionStatus.rejected, approved_at=None)
    apply_update(row, QuizQuestionUpdate(status=QuizQuestionStatus.approved), NOW)
    assert row.approved_at == NOW


def test_an_approved_row_without_a_stamp_is_repaired() -> None:
    """`approved` with no `approved_at` is not a state this code writes — a row
    edited by hand can carry it. Stamping beats leaving the contradiction."""
    row = make_row(QuizQuestionStatus.approved, approved_at=None)
    apply_update(row, QuizQuestionUpdate(status=QuizQuestionStatus.approved), NOW)
    assert row.approved_at == NOW


def test_resending_the_identical_text_is_not_an_edit() -> None:
    """The board round-trips all four content fields when saving one of them —
    an unchanged value must not withdraw the approval."""
    row = make_row(QuizQuestionStatus.approved, approved_at=YESTERDAY)
    apply_update(
        row,
        QuizQuestionUpdate(
            question=row.question,
            options=list(row.options),
            correct_answer=row.correct_answer,
            explanation=row.explanation,
        ),
        NOW,
    )
    assert row.status == "approved"
    assert row.approved_at == YESTERDAY


def test_editing_a_pending_question_leaves_it_pending() -> None:
    row = make_row(QuizQuestionStatus.pending)
    apply_update(row, QuizQuestionUpdate(explanation="Neue Begründung."), NOW)
    assert row.explanation == "Neue Begründung."
    assert row.status == "pending"
    assert row.approved_at is None


# ---- QuizQuestionUpdate: what the body refuses ----------------------------


@pytest.mark.parametrize("field", ["document_id", "chunk_id", "source_excerpt"])
def test_evidence_fields_are_not_writable(field: str) -> None:
    with pytest.raises(ValueError):
        QuizQuestionUpdate(**{field: str(uuid.uuid4())})


def test_empty_body_is_rejected() -> None:
    with pytest.raises(ValueError):
        QuizQuestionUpdate()


def test_explicit_null_is_rejected() -> None:
    """`{"status": null}` is a contract violation, not a way to clear a NOT NULL
    column — nothing in openapi.yaml declares these fields nullable."""
    with pytest.raises(ValueError):
        QuizQuestionUpdate(status=None)


# ---- GET /quiz/questions --------------------------------------------------


async def test_get_returns_a_page_with_its_total() -> None:
    rows = [make_row(QuizQuestionStatus.approved) for _ in range(2)]
    override(make_user("knowledge_owner"), make_list_db(rows, total=7))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["total"] == 7


async def test_total_is_independent_of_limit() -> None:
    """The count query carries the filter but neither limit nor offset — a
    column's count must not shrink to the size of the page being shown."""
    db = make_list_db([make_row(QuizQuestionStatus.approved)], total=42)
    override(make_user("knowledge_owner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions?limit=1")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    assert r.json()["total"] == 42
    assert "LIMIT" not in compiled(db.scalar.await_args).upper()


async def test_learner_asking_for_pending_gets_an_empty_page_not_403() -> None:
    db = make_list_db([])
    override(make_user("learner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions?status=pending")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0}
    # Provably nothing to return, so the database is never asked.
    db.execute.assert_not_awaited()
    db.scalar.assert_not_awaited()


async def test_learner_without_filter_queries_only_approved() -> None:
    db = make_list_db([make_row(QuizQuestionStatus.approved)])
    override(make_user("learner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions")
    assert r.status_code == 200
    # The role reached the SQL, not just the response: both the count and the
    # page are restricted to the one status a learner may see.
    for call in (db.scalar.await_args, db.execute.await_args):
        assert "'approved'" in compiled(call)
        assert "'pending'" not in compiled(call)


async def test_reviewer_filter_reaches_the_sql() -> None:
    db = make_list_db([make_row(QuizQuestionStatus.rejected)])
    override(make_user("knowledge_owner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions?status=rejected")
    assert r.status_code == 200
    assert "'rejected'" in compiled(db.execute.await_args)
    assert "'approved'" not in compiled(db.execute.await_args)


@pytest.mark.parametrize("query", ["?limit=201", "?limit=0", "?offset=-1", "?status=freigegeben"])
async def test_invalid_query_parameters_are_422(query: str) -> None:
    override(make_user("knowledge_owner"), make_list_db([]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/quiz/questions{query}")
    assert r.status_code == 422
    assert_validation_error_body(r.json())


async def test_get_without_token_is_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions")
    assert r.status_code == 401


# ---- PATCH /quiz/questions/{question_id} ----------------------------------


async def test_patch_returns_the_updated_question() -> None:
    row = make_row()
    override(make_user("knowledge_owner"), make_patch_db(row))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.patch(f"/quiz/questions/{row.id}", json={"status": "approved"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(row.id)
    assert body["status"] == "approved"
    assert body["approved_at"] is not None


async def test_patch_by_a_learner_is_403() -> None:
    row = make_row()
    override(make_user("learner"), make_patch_db(row))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.patch(f"/quiz/questions/{row.id}", json={"status": "approved"})
    assert r.status_code == 403


async def test_patch_of_an_unknown_id_is_404() -> None:
    override(make_user("knowledge_owner"), make_patch_db(None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.patch(f"/quiz/questions/{uuid.uuid4()}", json={"status": "approved"})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"source_excerpt": "umgeschrieben"}, id="evidence-field"),
        pytest.param({"document_id": "11111111-1111-1111-1111-111111111111"}, id="document-id"),
        pytest.param({"options": ["A", "B", "C"]}, id="three-options"),
        pytest.param({"options": ["A", "B", "C", "D", "E"]}, id="five-options"),
        pytest.param({"correct_answer": "E"}, id="answer-outside-a-to-d"),
        pytest.param({"status": "freigegeben"}, id="unknown-status"),
        pytest.param({}, id="empty-body"),
        pytest.param({"question": ""}, id="empty-question"),
    ],
)
async def test_patch_rejects_an_invalid_body_with_422(body: dict[str, Any]) -> None:
    row = make_row()
    override(make_user("knowledge_owner"), make_patch_db(row))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.patch(f"/quiz/questions/{row.id}", json=body)
    assert r.status_code == 422
    assert_validation_error_body(r.json())


# ---- GET /quiz/questions/sample -------------------------------------------


@pytest.mark.parametrize("role", ["learner", "knowledge_owner", "admin"])
async def test_sample_draws_only_approved_for_every_role(role: str) -> None:
    """Unlike the list, this endpoint does not widen with the role: a reviewer
    looking at the quiz is looking at what the learner gets."""
    db = make_list_db([make_row(QuizQuestionStatus.approved)])
    override(make_user(role), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions/sample")
    assert r.status_code == 200
    sql = compiled(db.execute.await_args)
    assert "'approved'" in sql
    assert "'pending'" not in sql and "'rejected'" not in sql


async def test_sample_draws_at_random_in_sql() -> None:
    """The draw belongs in the database: sorting by `created_at` and paging
    would hand out the same five newest questions on every run, and picking in
    the client means shipping the whole approved pool to the browser first."""
    db = make_list_db([make_row(QuizQuestionStatus.approved)])
    override(make_user("learner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions/sample")
    assert r.status_code == 200
    sql = compiled(db.execute.await_args)
    assert "random()" in sql.lower()
    assert f"LIMIT {QUIZ_LENGTH}" in sql


async def test_sample_reports_the_pool_size_as_total() -> None:
    rows = [make_row(QuizQuestionStatus.approved) for _ in range(QUIZ_LENGTH)]
    override(make_user("learner"), make_list_db(rows, total=37))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions/sample")
    assert r.status_code == 200
    assert len(r.json()["items"]) == QUIZ_LENGTH
    assert r.json()["total"] == 37


async def test_empty_pool_is_an_empty_sample_not_an_error() -> None:
    """The area holds what it holds — fewer than five, down to none, is a
    normal result and the quiz UI says so (same rule as sample_chunks)."""
    override(make_user("learner"), make_list_db([], total=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions/sample")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0}


async def test_sample_without_token_is_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions/sample")
    assert r.status_code == 401


async def test_sample_is_not_swallowed_by_the_patch_path() -> None:
    """`sample` must reach its own route and not be read as a question id."""
    db = make_list_db([make_row(QuizQuestionStatus.approved)])
    override(make_user("learner"), db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/quiz/questions/sample")
    assert r.status_code == 200
    db.get.assert_not_awaited()
