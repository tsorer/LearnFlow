import uuid
from datetime import UTC, datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_knowledge_owner
from app.database import get_db
from app.models.tables import Answer, Feedback, QuerySession, User

router = APIRouter(prefix="/answers", tags=["feedback"])

# Separate router (own prefix `/feedback`, not `/answers/{answer_id}/feedback`):
# the GET below reads the whole list and belongs to no single answer.
read_router = APIRouter(prefix="/feedback", tags=["feedback"])

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class FeedbackCategory(str, Enum):
    verstaendlich = "verstaendlich"
    vollstaendig = "vollstaendig"
    hilfreich_fuer_code = "hilfreich_fuer_code"
    quelle_passt_gut = "quelle_passt_gut"
    faktisch_falsch = "faktisch_falsch"
    unvollstaendig = "unvollstaendig"
    veraltet = "veraltet"
    unverstaendlich = "unverstaendlich"
    quelle_stimmt_nicht = "quelle_stimmt_nicht"


POSITIVE_CATEGORIES = {
    FeedbackCategory.verstaendlich,
    FeedbackCategory.vollstaendig,
    FeedbackCategory.hilfreich_fuer_code,
    FeedbackCategory.quelle_passt_gut,
}
NEGATIVE_CATEGORIES = {
    FeedbackCategory.faktisch_falsch,
    FeedbackCategory.unvollstaendig,
    FeedbackCategory.veraltet,
    FeedbackCategory.unverstaendlich,
    FeedbackCategory.quelle_stimmt_nicht,
}

# Both sets are enumerated explicitly rather than one derived from the other by
# exclusion: a category added to the enum later (T-31 touches this) without an
# update here would otherwise fall silently into whichever set isn't explicit,
# and no test would fail. This fails loudly at import time instead.
if POSITIVE_CATEGORIES | NEGATIVE_CATEGORIES != set(FeedbackCategory):
    raise ValueError("FeedbackCategory has member(s) in neither POSITIVE_ nor NEGATIVE_CATEGORIES")
if POSITIVE_CATEGORIES & NEGATIVE_CATEGORIES:
    raise ValueError("FeedbackCategory has member(s) in both POSITIVE_ and NEGATIVE_CATEGORIES")


class FeedbackRequest(BaseModel):
    helpful: bool
    category: FeedbackCategory | None = None
    comment: str | None = Field(default=None, max_length=500)


@router.post(
    "/{answer_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def create_feedback(
    answer_id: uuid.UUID,
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Pseudonymised by design — the table holds no user reference (US-03, ERD).

    The ownership check below only gates who may *write* a rating; nothing
    from it ends up in the `feedback` row.
    """
    answer = await db.get(Answer, answer_id)
    if answer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antwort nicht gefunden")

    # Same 404 for "does not exist" and "not yours" as documents.py's
    # PILOT_AREA check -- a different status would itself leak which
    # answer_ids belong to someone else's session. An anonymous session
    # (user_id NULL) has no specific owner to protect, so any authenticated
    # user may rate it.
    session = await db.get(QuerySession, answer.session_id)
    if session is not None and session.user_id is not None and session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antwort nicht gefunden")

    if body.category is not None:
        valid = POSITIVE_CATEGORIES if body.helpful else NEGATIVE_CATEGORIES
        if body.category not in valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kategorie passt nicht zu helpful",
            )

    # Upsert on the unique answer_id constraint (0011): a retry after a
    # timeout, a second tab, or a component remount updates the existing
    # rating instead of writing a second, unpseudonymisable row for the same
    # answer. Done as one atomic statement, not a select-then-branch, so two
    # concurrent submissions can't both see "no row yet" and both insert.
    insert_stmt = pg_insert(Feedback).values(
        id=uuid.uuid4(),
        answer_id=answer_id,
        helpful=body.helpful,
        category=body.category.value if body.category else None,
        comment=body.comment,
        created_at=datetime.now(UTC),
    )
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[Feedback.answer_id],
        set_={
            "helpful": insert_stmt.excluded.helpful,
            "category": insert_stmt.excluded.category,
            "comment": insert_stmt.excluded.comment,
        },
    )
    await db.execute(upsert_stmt)
    await db.commit()


class FeedbackItem(BaseModel):
    """One row of Stefan's area overview (T-32).

    No `answer_id` and nothing derived from `answers`/`query_sessions` --
    pseudonymisation stays end to end, not just at the `feedback` table
    (openapi.yaml, GET /api/feedback).
    """

    id: uuid.UUID
    helpful: bool
    category: FeedbackCategory | None
    comment: str | None
    created_at: datetime


class FeedbackPage(BaseModel):
    items: list[FeedbackItem]
    total: int


def _to_item(row: Feedback) -> FeedbackItem:
    try:
        category = FeedbackCategory(row.category) if row.category is not None else None
    except ValueError:
        # `category` has no DB CHECK (unlike quiz_questions.status) and a value
        # outside the current enum -- a category renamed or removed after this
        # row was written -- must not 500 the whole dashboard for every other
        # row. Surfaced as "no category" for this one row instead.
        category = None
    return FeedbackItem(
        id=row.id,
        helpful=row.helpful,
        category=category,
        comment=row.comment,
        created_at=row.created_at,
    )


@read_router.get("", response_model=FeedbackPage, dependencies=[Depends(require_knowledge_owner)])
async def list_feedback(
    helpful: bool | None = Query(None),
    category: FeedbackCategory | None = Query(None),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> FeedbackPage:
    filters = []
    if helpful is not None:
        filters.append(Feedback.helpful == helpful)
    if category is not None:
        filters.append(Feedback.category == category.value)

    # Counted separately and without limit/offset -- the dashboard needs the
    # size of the filtered set, not the size of the page it happens to show
    # (same reasoning as list_questions in app/routers/quiz.py).
    total = await db.scalar(select(func.count()).select_from(Feedback).where(*filters))
    result = await db.execute(
        select(Feedback)
        # `id` as the tie-breaker: rows from the same instant would otherwise
        # leave the order of a paged query undefined (same reasoning as
        # list_questions in app/routers/quiz.py).
        .where(*filters)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [_to_item(row) for row in result.scalars().all()]
    return FeedbackPage(items=items, total=total or 0)
