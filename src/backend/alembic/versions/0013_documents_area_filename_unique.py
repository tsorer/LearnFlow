"""Make (area, filename) unique -- one document per filename and area (T-15)

An upload of a filename that already exists in the area now replaces that
document instead of adding a second one with the same name. Nothing stopped
duplicates from being created before, so the rows that predate T-15 can still
hold several documents under one name -- and with them, the upload route could
only ever pick one to replace and would silently leave the others behind.

The delete keeps the newest row per (area, filename) and drops the rest; their
chunks follow through the existing ON DELETE CASCADE. `updated_at` is what
ranks them, being the timestamp of the version a row currently holds, with the
id breaking a tie so the outcome does not depend on the physical row order.

Safe here because the pilot has no production data yet (Ops/07). On a database
that has any, this migration destroys the older duplicates of a name, and the
choice of which copy survives belongs to whoever owns those documents, not to
this script.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-20
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DELETE FROM documents older
              USING documents newer
              WHERE older.area = newer.area
                AND older.filename = newer.filename
                AND (older.updated_at, older.id) < (newer.updated_at, newer.id)
    """)
    op.create_index(
        "ix_documents_area_filename", "documents", ["area", "filename"], unique=True
    )


def downgrade() -> None:
    # The deleted duplicates do not come back -- only the constraint goes.
    op.drop_index("ix_documents_area_filename", table_name="documents")
