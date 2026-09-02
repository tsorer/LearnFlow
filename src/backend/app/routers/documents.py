import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.auth.dependencies import require_knowledge_owner
from app.database import get_db
from app.models.tables import (
    Chunk,
    Document,
    DocumentStatus,
    QuizQuestion,
    QuizQuestionStatus,
    User,
)
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
    # The spec types this field as the DocumentStatus enum, so the response
    # model does too: a row holding anything else fails here instead of being
    # served to a client whose generated types cannot represent it.
    status: DocumentStatus
    area: str
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    # E-Mail statt der rohen uploaded_by-UUID: die Upload-UI nennt den bisherigen
    # Hochladenden vor einer Ersetzung (#92), und eine UUID sagt niemandem etwas.
    # null, wenn das Konto seither gelöscht wurde (FK ON DELETE SET NULL).
    uploaded_by: str | None = None


def _to_response(document: Document, uploader_email: str | None) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        # The column is a plain varchar, so the conversion happens here: a value
        # outside the enum raises instead of reaching a client that has no type
        # for it. Only this router and the worker write the column, both from
        # DocumentStatus, so the only way to hit it is by editing the row by hand.
        # The radius is deliberate: in GET /documents one such row takes the
        # whole list down with it rather than the list serving a status no
        # client can render (review on #87).
        status=DocumentStatus(document.status),
        area=document.area,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
        uploaded_by=uploader_email,
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
    # Outer-Join auf users: uploaded_by ist nullbar (gelöschtes Konto), ein
    # Inner-Join würde solche Dokumente aus der Liste fallen lassen.
    result = await db.execute(
        select(Document, User.email)
        .options(defer(Document.content))
        .outerjoin(User, Document.uploaded_by == User.id)
        .where(Document.area == PILOT_AREA)
        .order_by(Document.created_at.desc())
    )
    return [_to_response(doc, email) for doc, email in result.all()]


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_200_OK: {"model": DocumentResponse}},
)
async def upload_document(
    response: Response,
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

    existing = await _find_by_filename(filename, area, db)
    if existing is None:
        uploaded_at = datetime.now(UTC)
        document = Document(
            id=uuid.uuid4(),
            filename=filename,
            content_type=ALLOWED_CONTENT_TYPES[ext],
            content=content,
            status=DocumentStatus.pending,
            area=area,
            uploaded_by=user.id,
            chunk_count=0,
            error_message=None,
            created_at=uploaded_at,
            # Same moment as created_at until the document is replaced. Set here
            # rather than left to the server default: the session does not
            # expire objects on commit, so an attribute the database fills in
            # would still be None in the response below.
            updated_at=uploaded_at,
            # The first version, with its attempts untouched. Set here for the
            # same reason as updated_at: the server default would leave the
            # attribute None on the object this request answers from.
            index_version=1,
            index_attempts=0,
        )
        db.add(document)
    else:
        document = await _replace(existing, content, ALLOWED_CONTENT_TYPES[ext], user, db)
        response.status_code = status.HTTP_200_OK

    # Lookup, chunk deletion, update and enqueue share one transaction: if
    # anything fails, the previous version stays intact and indexed.
    await enqueue_document(db, str(document.id))
    await db.commit()

    # Beide Pfade (Neuanlage wie Ersetzung) setzen uploaded_by auf user.id, also
    # ist der Hochladende hier immer der aktuelle User — kein Nachladen nötig.
    return _to_response(document, user.email)


async def _find_by_filename(filename: str, area: str, db: AsyncSession) -> Document | None:
    """The document a new upload of `filename` replaces (T-15), if there is one.

    Matched on the exact filename — no case folding, no normalisation: the name
    is what the uploader sees in the list, and two names that differ visibly
    should not silently collapse into one document.

    At most one row can match: `ix_documents_area_filename` is unique (migration
    0013). FOR UPDATE serialises two uploads of the same name against each
    other, so the second one finds the row the first one wrote and replaces it
    instead of racing it into that constraint.
    """
    result = await db.execute(
        # defer(content): the old payload is overwritten a moment later, so the
        # up to 10 MB bytea (ADR-003) never has to leave the database.
        select(Document)
        .options(defer(Document.content))
        .where(Document.area == area, Document.filename == filename)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _replace(
    document: Document, content: bytes, content_type: str, user: User, db: AsyncSession
) -> Document:
    """Turn an existing document into the newly uploaded version of itself.

    The row is updated instead of replaced so the id survives: the frontend
    polls it, and answers and quiz questions reference it.

    The old chunks go now, not when the worker re-indexes. Retrieval reads only
    chunks of `status = 'available'` documents, so the status reset alone
    already takes the replaced version out of every answer (ADR-008
    fail-closed). Deleting the rows here makes that independent of the
    re-indexing run: whether it succeeds, fails or never starts, the content of
    a version the owner has replaced is gone from the database — instead of
    sitting in the index waiting for the visibility rule to change.
    """
    await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
    # The quiz questions of the old version survive the replacement but lose
    # their approval (decision on #40, T-33). Deleting them would throw away
    # Stefan's review silently; leaving them approved would keep questions in
    # the learners' pool that were checked against a text nobody can read any
    # more. So they go back into the queue and he decides again — approve, or
    # reject if the new version no longer supports the question.
    #
    # Only approved ones. A question he has already rejected stays rejected;
    # putting it in front of him again would be work he has done.
    #
    # `chunk_id` needs no statement here: the delete above takes the chunks with
    # it, and the FK sets the reference to NULL (migration 0016). That NULL is
    # what tells this case apart from a freshly generated question in the review
    # — one of those always has a chunk.
    await db.execute(
        update(QuizQuestion)
        .where(
            QuizQuestion.document_id == document.id,
            QuizQuestion.status == QuizQuestionStatus.approved,
        )
        .values(status=QuizQuestionStatus.pending, approved_at=None)
    )
    # created_at keeps pointing at the first upload, updated_at at this one —
    # the pair is what tells a replacement apart from a first upload in GET
    # /documents. Assigned instead of left to the column's onupdate for the
    # same reason as on the insert path: with expire_on_commit=False the
    # response would otherwise carry the value from before the replacement.
    document.updated_at = datetime.now(UTC)
    # New bytes, so every run that is still indexing the old ones is void
    # (T-43): the token moves, and their publish fails the guard in
    # `worker/main.py`. Incremented rather than set to a timestamp — this is
    # the column `updated_at` used to double as, and the reason it no longer
    # has to. The attempts start over with the new version.
    document.index_version = document.index_version + 1
    document.index_attempts = 0
    document.content = content
    document.content_type = content_type
    document.status = DocumentStatus.pending
    document.chunk_count = 0
    document.error_message = None
    # The new version has not been through validation (US-06), whatever the
    # replaced one had reached.
    document.validated_at = None
    # Moves with the content, like every other column here — the row describes
    # the version it currently holds, and `created_at` is the one documented
    # exception (spec: the first upload, surviving a replacement). So the pair
    # reads as "in the corpus since T1, current text put there by this person";
    # who uploaded the version that is gone is not kept (review on #87).
    document.uploaded_by = user.id
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    document = await _get_pilot_area_document(document_id, db)
    uploader_email = (
        await db.scalar(select(User.email).where(User.id == document.uploaded_by))
        if document.uploaded_by is not None
        else None
    )
    return _to_response(document, uploader_email)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(require_knowledge_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    document = await _get_pilot_area_document(document_id, db)
    await db.delete(document)  # Chunk rows cascade via ondelete="CASCADE" (0003)
    await db.commit()
