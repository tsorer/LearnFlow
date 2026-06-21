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


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        text("SELECT status FROM pgqueuer WHERE id = :id"),
        {"id": job_id},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    raw_status: str = row[0]
    return {"job_id": str(job_id), "status": _STATUS_MAP.get(raw_status, raw_status)}
