import uuid
from datetime import UTC, datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.tables import Answer, Feedback

router = APIRouter(prefix="/answers", tags=["feedback"])


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
NEGATIVE_CATEGORIES = set(FeedbackCategory) - POSITIVE_CATEGORIES


class FeedbackRequest(BaseModel):
    helpful: bool
    category: FeedbackCategory | None = None
    comment: str | None = Field(default=None, max_length=500)


@router.post(
    "/{answer_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user)],
)
async def create_feedback(
    answer_id: uuid.UUID,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Pseudonymised by design — the table holds no user reference (US-03, ERD)."""
    answer = await db.get(Answer, answer_id)
    if answer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antwort nicht gefunden")

    if body.category is not None:
        valid = POSITIVE_CATEGORIES if body.helpful else NEGATIVE_CATEGORIES
        if body.category not in valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kategorie passt nicht zu helpful",
            )

    db.add(
        Feedback(
            id=uuid.uuid4(),
            answer_id=answer_id,
            helpful=body.helpful,
            category=body.category.value if body.category else None,
            comment=body.comment,
            created_at=datetime.now(UTC),
        )
    )
    await db.commit()
