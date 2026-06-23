"""Create RAG runtime tables: query_sessions, answers, feedback, config

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-17
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_query_sessions_user_id",
        ),
    )
    op.create_index("ix_query_sessions_user_id", "query_sessions", ["user_id"])

    op.create_table(
        "answers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer_text", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("citation_coverage", sa.Float, nullable=True),
        sa.Column("retrieval_confidence", sa.Float, nullable=True),
        sa.Column("suppressed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["query_sessions.id"],
            ondelete="CASCADE",
            name="fk_answers_session_id",
        ),
    )
    op.create_index("ix_answers_session_id", "answers", ["session_id"])

    op.create_table(
        "feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("answer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("helpful", sa.Boolean, nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # pseudonymised — no user_id (US-03)
        sa.ForeignKeyConstraint(
            ["answer_id"],
            ["answers.id"],
            ondelete="CASCADE",
            name="fk_feedback_answer_id",
        ),
    )

    op.create_table(
        "config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("changed_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_config_changed_by",
        ),
    )

    # Seed default config values (ADR-007 / ADR-008 start values — calibrate in spike)
    rows = [
        ("similarity_threshold",     "0.35", "Min cosine similarity for retrieval gate (ADR-007)"),
        ("min_retrieval_confidence",  "0.40", "Min retrieval confidence score (ADR-008 stage 1)"),
        ("min_citation_coverage",     "0.50", "Min citation coverage before suppression (ADR-008)"),
        ("stale_days",                "90",   "Days until a document is considered stale (US-06)"),
        ("rrf_k",                     "60",   "Reciprocal Rank Fusion k parameter (ADR-007)"),
        ("retrieval_top_k",           "20",   "Candidates retrieved per search type (ADR-007)"),
        ("context_top_n",             "5",    "Chunks passed to the LLM as context (ADR-007)"),
    ]
    for key, value, description in rows:
        op.execute(
            sa.text(
                "INSERT INTO config (key, value, description) VALUES (:key, :value, :description)"
            ),
            {"key": key, "value": value, "description": description},
        )


def downgrade() -> None:
    op.drop_table("config")
    op.drop_table("feedback")
    op.drop_table("answers")
    op.drop_table("query_sessions")
