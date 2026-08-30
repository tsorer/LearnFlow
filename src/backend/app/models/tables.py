import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, Enum):
    learner = "learner"
    knowledge_owner = "knowledge_owner"
    admin = "admin"


class DocumentStatus(str, Enum):
    """The stages a document passes through, mirroring the `DocumentStatus`
    enum of openapi.yaml — the values are part of the API contract, not an
    internal detail. `tests/test_openapi_spec.py` keeps the two in step.

    Written by the API on upload (pending) and by the worker as it indexes;
    `available` is what makes a document's chunks visible to retrieval
    (`app/services/retrieval.py`).
    """

    pending = "pending"
    processing = "processing"
    available = "available"
    failed = "failed"


class QuizQuestionStatus(str, Enum):
    """Where a generated question stands in Stefan's review (US-07).

    Mirrors the `QuizQuestionStatus` schema of openapi.yaml — the values are
    part of the API contract, not an internal detail, and
    `tests/test_openapi_spec.py` keeps the two in step. The database holds the
    same three values as a CHECK constraint (migration 0016), because the
    generation endpoint is not the only writer: T-35 edits these rows too.

    `pending` is the default in the column, so a question nobody has looked at
    can never be mistaken for an approved one (ADR-008, fail-closed). A question
    whose document was replaced is put back here (documents.py `_replace`).
    """

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default=UserRole.learner)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"
    # One document per filename and area (T-15): an upload of a name that is
    # already there replaces it. Declared here as well as in migration 0013 so
    # the model's metadata describes the schema that actually exists.
    __table_args__ = (Index("ix_documents_area_filename", "area", "filename", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=DocumentStatus.pending.value
    )
    area: Mapped[str] = mapped_column(String(100), nullable=False, server_default="default")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Read as a version token, not just as a timestamp: the worker takes it with
    # the content and refuses to publish an indexing run whose row no longer
    # carries the same value (worker/main.py, mark_available). `onupdate` moves
    # it on *any* ORM write to this row, so a future route that writes a
    # Document for an unrelated reason would make a job that is indexing this
    # document right now discard its work silently, logged as info and reported
    # as nothing. The reaper of T-43 is the nearest such writer: it exists to
    # move rows out of a stuck 'processing', and its own criterion is that a
    # document currently being processed stays untouched.
    # A write that does not mean "this is a new version of the file" therefore
    # has to preserve updated_at, or the guard needs a column of its own.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (Index("ix_chunks_document_id", "document_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Any: pgvector and tsvector have no SQLAlchemy-native Python type
    embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=True)
    tsv: Mapped[Any] = mapped_column(TSVECTOR, nullable=True)


class QuerySession(Base):
    __tablename__ = "query_sessions"
    __table_args__ = (Index("ix_query_sessions_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (Index("ix_answers_session_id", "session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("query_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # NULL means stage 3 never ran, which is the normal case — it only fires
    # inside the trigger band (ADR-008, T-25). A default of false would make
    # every skipped self-check look like a failed one.
    self_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # unique: one rating per answer (upsert on repeat submission) -- a retry, a
    # second tab, or a component remount must update the same row instead of
    # writing an unpseudonymisable duplicate that inflates T-32's aggregation.
    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("answers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Config(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuizQuestion(Base):
    """One generated multiple-choice question awaiting or carrying a verdict.

    `options` is a JSON array of exactly four strings (a CHECK enforces the
    count) and `correct_answer` is the label "A" to "D" indexing it. Two
    columns rather than a flag per option, because that is the shape the LLM
    returns and the shape T-36 renders.

    `chunk_id` and `source_excerpt` are the same fact recorded twice on
    purpose. The reference is the live link into the corpus; the excerpt is the
    copy that outlives it. Deleting a chunk sets the reference to NULL instead
    of deleting the question (migration 0016), so `chunk_id IS NULL` reads as
    "the version this was generated from has been replaced" — a question in
    that state is back at `pending` and Stefan judges it against the excerpt.
    """

    __tablename__ = "quiz_questions"
    __table_args__ = (
        Index("ix_quiz_questions_document_id", "document_id"),
        Index("ix_quiz_questions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # Any: JSONB has no direct Python type mapping
    options: Mapped[Any] = mapped_column(JSONB, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(10), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=QuizQuestionStatus.pending.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # NULL until someone approves. Written by T-35, not by the generation
    # endpoint: US-07 asks for the moment of the approval, and `created_at`
    # answers a different question (when the model wrote it).
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
