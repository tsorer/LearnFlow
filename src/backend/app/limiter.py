from fastapi import Request
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth.jwt import decode_token

limiter = Limiter(key_func=get_remote_address)


def account_key(request: Request) -> str:
    """Rate-limit key for authenticated endpoints: the account, not the address.

    /auth/login counts per client IP on purpose — it has no account yet, and a
    per-account counter there could be tripped from any address to lock the real
    user out. Behind a valid token that argument is gone: a stranger cannot spend
    someone else's budget without their token. Meanwhile the cost of counting per
    IP grows, because the pilot users sit behind one NAT address and asking
    questions is the normal case, not the exception — one heavy asker would lock
    out the whole office (Docs/03_QualityAttributes.md, Security).

    The subject comes from the header rather than from `get_current_user`,
    because slowapi hands the key function the raw request and nothing else.
    """
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            subject = decode_token(token).get("sub")
        except JWTError:
            subject = None
        if subject:
            return f"account:{subject}"
    # A request without a usable token is rejected with 401 by the endpoint's
    # dependency before the limiter ever counts it. The fallback is here so the
    # key is always defined, not because this path carries its own policy.
    return f"address:{get_remote_address(request)}"
