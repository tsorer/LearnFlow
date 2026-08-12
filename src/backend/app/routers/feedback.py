import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/answers", tags=["feedback"])


@router.post("/{answer_id}/feedback", dependencies=[Depends(get_current_user)])
async def create_feedback(answer_id: uuid.UUID) -> None:
    """Placeholder so contract and implementation stay symmetric.

    TODO (T-30): persist into `feedback` (answer_id, helpful, category,
    comment). Pseudonymised by design — the table holds no user reference
    (US-03, ERD).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Noch nicht implementiert (T-30)",
    )
