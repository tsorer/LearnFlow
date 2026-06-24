"""Job status endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])

_STATUS_MAP: dict[str, str] = {
    "queued": "pending",
    "picked": "processing",
    "successful": "done",
    "exception": "failed",
    "canceled": "failed",
    "deleted": "failed",
}


@router.get("/{document_id}/status")
async def get_job_status(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        text(
            "SELECT status FROM pgqueuer"
            " WHERE payload::jsonb->>'document_id' = :document_id"
            " ORDER BY id DESC LIMIT 1"
        ),
        {"document_id": str(document_id)},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    raw_status: str = row[0]
    return {"document_id": str(document_id), "status": _STATUS_MAP.get(raw_status, raw_status)}
