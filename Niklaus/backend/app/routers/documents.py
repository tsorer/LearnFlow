import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_knowledge_owner
from app.database import get_db
from app.models.tables import Document, User

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_BYTES = 10 * 1024 * 1024  # 10 MB per ADR-003
ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/markdown", "text/plain"}


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    area: str
    chunk_count: int
    created_at: str


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return [
        DocumentOut(
            id=str(d.id), filename=d.filename, status=d.status,
            area=d.area, chunk_count=d.chunk_count,
            created_at=d.created_at.isoformat(),
        )
        for d in rows.scalars()
    ]


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    area: str = Form(default="default"),
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    doc = Document(
        id=uuid.uuid4(),
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        area=area,
        uploaded_by=user.id,
        status="pending",
    )
    db.add(doc)
    await db.flush()

    # Enqueue processing job via pgqueuer
    from app.queue import enqueue_document
    await enqueue_document(db, str(doc.id))

    await db.commit()
    return DocumentOut(
        id=str(doc.id), filename=doc.filename, status=doc.status,
        area=doc.area, chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat(),
    )


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut(
        id=str(doc.id), filename=doc.filename, status=doc.status,
        area=doc.area, chunk_count=doc.chunk_count,
        created_at=doc.created_at.isoformat(),
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()
