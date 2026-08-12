import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.auth.dependencies import require_knowledge_owner
from app.database import get_db
from app.models.tables import Document, User
from app.queue import enqueue_document

router = APIRouter(prefix="/documents", tags=["documents"])

# MVP: genau ein hartcodierter Pilot-Bereich (Requirements §3) — User hat noch kein
# eigenes area-Feld. Sobald Bereiche pro User existieren, ersetzt user.area dies hier.
PILOT_AREA = "default"

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


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        area=document.area,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        created_at=document.created_at,
    )


async def _get_pilot_area_document(document_id: uuid.UUID, db: AsyncSession) -> Document:
    # defer(content): GET liefert kein content-Feld, DELETE braucht es nur zum Löschen
    # der Zeile — das bis zu 10 MB grosse bytea (ADR-003) muss dafür nicht geladen werden.
    document = await db.get(Document, document_id, options=[defer(Document.content)])
    # Gleiches 404 für "nicht gefunden" und "falscher Bereich" — die Existenz eines
    # fremden Dokuments soll ausserhalb des eigenen Bereichs nicht preisgegeben werden.
    if document is None or document.area != PILOT_AREA:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden")
    return document


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    # defer(content): DocumentResponse liefert kein content-Feld, das bis zu 10 MB
    # grosse bytea (ADR-003) soll daher gar nicht erst aus der DB geladen werden.
    result = await db.execute(
        select(Document)
        .options(defer(Document.content))
        .where(Document.area == PILOT_AREA)
        .order_by(Document.created_at.desc())
    )
    return [_to_response(d) for d in result.scalars().all()]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    area: str = Form(PILOT_AREA),
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    # 400, nicht 422: FastAPI nutzt 422 bereits für seine eigene Request-Validierung
    # (z.B. fehlende Datei) mit einer anderen Body-Form (Array statt String) — beides
    # unter demselben Code wäre ein uneindeutiger Vertrag für die generierten
    # Frontend-Typen (T-39).
    if area != PILOT_AREA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unbekannter Bereich (MVP: nur '{PILOT_AREA}')",
        )

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

    return _to_response(document)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    document = await _get_pilot_area_document(document_id, db)
    return _to_response(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    document = await _get_pilot_area_document(document_id, db)
    await db.delete(document)  # Chunk rows cascade via ondelete="CASCADE" (0003)
    await db.commit()
