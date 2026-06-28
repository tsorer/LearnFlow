"""Align documents.status default with the OpenAPI DocumentStatus enum

The column default was "queued", which is not part of the
DocumentStatus enum (pending, processing, available, failed) defined
in openapi.yaml. The API always sets "pending" explicitly on insert,
so this only affects the column default and any pre-existing "queued" rows.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-28
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE documents SET status = 'pending' WHERE status = 'queued'")
    op.alter_column("documents", "status", server_default="pending")


def downgrade() -> None:
    op.alter_column("documents", "status", server_default="queued")
