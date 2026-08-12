from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt as _bcrypt
from jose import jwt
from starlette.concurrency import run_in_threadpool

from app.config import settings


def _hash_password_sync(password: str) -> str:
    salt = _bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return _bcrypt.hashpw(password.encode(), salt).decode()


def _verify_password_sync(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# Hash of a value nobody can log in with, used to spend the same bcrypt time on an
# unknown e-mail as on a known one (see routers/auth.py). Built once at import with
# the configured cost so the two code paths stay indistinguishable by response time.
DUMMY_PASSWORD_HASH = _hash_password_sync("not-a-real-password")


# bcrypt is CPU-bound and takes ~0.3 s at the default cost of 12; running it inline
# in an async endpoint would block the whole event loop for that long.
async def hash_password(password: str) -> str:
    return await run_in_threadpool(_hash_password_sync, password)


async def verify_password(plain: str, hashed: str) -> bool:
    return await run_in_threadpool(_verify_password_sync, plain, hashed)


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(hours=settings.jwt_expire_hours))
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
