"""Tests for seed_users: validates the USERS data list."""

from seed_users import USERS


def test_all_roles_represented() -> None:
    roles = {u["role"] for u in USERS}
    assert "learner" in roles
    assert "knowledge_owner" in roles
    assert "admin" in roles


def test_passwords_are_plaintext_in_list() -> None:
    for u in USERS:
        assert not u["password"].startswith("$2b$"), (
            f"{u['email']}: password must be plaintext in USERS list, not a bcrypt hash"
        )
