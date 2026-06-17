"""Unit tests for seed_users.py — role coverage and bcrypt hashing."""

import bcrypt as _bcrypt

from seed_users import USERS


def test_all_roles_represented() -> None:
    roles = {u["role"] for u in USERS}
    assert "learner" in roles
    assert "knowledge_owner" in roles
    assert "admin" in roles


def test_passwords_are_bcrypt_hashed() -> None:
    for u in USERS:
        password = u["password"].encode()
        hashed = _bcrypt.hashpw(password, _bcrypt.gensalt())
        assert _bcrypt.checkpw(password, hashed)
        # Ensure the stored password is not stored as plaintext
        assert not u["password"].startswith("$2b$")
