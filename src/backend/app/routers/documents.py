import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_knowledge_owner
from app.database import get_db
from app.models.tables import Document, User
from app.queue import enqueue_document

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # ADR-003: hartes 10-MB-Limit

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    area: str
    chunk_count: int
    error_message: str | None
    created_at: datetime


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    area: str = Form("default"),
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Nicht unterstütztes Dateiformat (erlaubt: PDF, DOCX, Markdown)",
        )

    # file.size is set by Starlette from the actually received bytes (not the
    # spoofable Content-Length header) — reject oversized uploads before
    # materializing the payload into memory via read().
    too_large = file.size is not None and file.size > MAX_UPLOAD_BYTES
    content = b"" if too_large else await file.read()
    if too_large or len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Datei überschreitet das 10-MB-Limit",
        )

    document = Document(
        id=uuid.uuid4(),
        filename=filename,
        content_type=ALLOWED_CONTENT_TYPES[ext],
        content=content,
        status="pending",
        area=area,
        uploaded_by=user.id,
        chunk_count=0,
        error_message=None,
        created_at=datetime.now(UTC),
    )
    db.add(document)
    await enqueue_document(db, str(document.id))
    await db.commit()

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        area=document.area,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        created_at=document.created_at,
    )
