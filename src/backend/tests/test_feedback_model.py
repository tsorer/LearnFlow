"""Structural tests for the `feedback` table (T-29).

Static assertions against SQLAlchemy metadata — no DB connection needed,
mirroring how the rest of the suite avoids a live Postgres for pure model
checks.
"""

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.tables import Feedback

TABLE = Feedback.__table__


def test_columns_and_types() -> None:
    columns = TABLE.columns

    assert isinstance(columns["id"].type, UUID)
    assert columns["id"].primary_key

    assert isinstance(columns["answer_id"].type, UUID)
    assert not columns["answer_id"].nullable

    assert isinstance(columns["helpful"].type, Boolean)
    assert not columns["helpful"].nullable

    assert isinstance(columns["category"].type, String)
    assert columns["category"].type.length == 100
    assert columns["category"].nullable

    assert isinstance(columns["comment"].type, Text)
    assert columns["comment"].nullable

    assert isinstance(columns["created_at"].type, DateTime)
    assert not columns["created_at"].nullable


def test_answer_id_foreign_key_cascades() -> None:
    (fk,) = TABLE.columns["answer_id"].foreign_keys
    assert fk.target_fullname == "answers.id"
    assert fk.ondelete == "CASCADE"


def test_answer_id_is_uniquely_indexed() -> None:
    """Unique, not just indexed: the endpoint upserts on this (one rating per
    answer, review on #81) — a plain index here would let ON CONFLICT silently
    stop matching."""
    (index,) = (i for i in TABLE.indexes if i.name == "ix_feedback_answer_id")
    assert [c.name for c in index.columns] == ["answer_id"]
    assert index.unique


def test_no_user_reference_column() -> None:
    """Pseudonymization is by omission, not hashing (US-03, ERD, T-30) —
    guard against a `user_id`/hash column being reintroduced later."""
    column_names = set(TABLE.columns.keys())
    assert not any("user" in name or "hash" in name for name in column_names)
