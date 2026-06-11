import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.tables import Answer, Feedback, User

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


@router.post("/answers/{answer_id}/feedback", status_code=201)
async def submit_feedback(
    answer_id: str,
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    answer = await db.get(Answer, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    # Pseudonymize user identifier
    user_hash = hashlib.sha256(str(user.id).encode()).hexdigest()

    fb = Feedback(
        id=uuid.uuid4(),
        answer_id=uuid.UUID(answer_id),
        user_hash=user_hash,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(fb)
    await db.commit()
    return {"message": "feedback recorded"}
