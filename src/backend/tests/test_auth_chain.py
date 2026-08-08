"""T-09: die Auth-Kette in-process, ohne laufenden Stack.

Die bestehenden Tests decken je nur ein Ende der Kette ab: `test_auth.py` hoert beim
ausgestellten Token auf, `test_documents.py` ersetzt `get_current_user` per
`dependency_overrides` und umgeht damit genau den Teil, der Login und geschuetzte
Route verbindet. Hier laeuft der ganze Weg — Login -> JWT -> Dekodierung ->
User-Lookup -> geschuetzte Route — durch die echte Dependency-Kette; ersetzt ist
nur die Datenbank.

Das ist ein Integrationstest, kein End-to-End-Test: Browser, nginx und Postgres
fehlen. Die Nahtstellen dorthin deckt `e2e/test_login_flow.py` ab. Der Wert dieser
Datei ist, dass sie ohne Container in Sekunden laeuft und die Fehlerfaelle
(abgelaufen, fremd signiert, User geloescht, deaktiviert) billig durchspielt.
"""

import asyncio
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from jose import jwt
from sqlalchemy import Select

from app.auth.jwt import create_access_token, hash_password
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.main import app
from app.models.tables import User

EMAIL = "lara@learnflow.ch"
PASSWORD = "correct-horse-battery-staple"
# Ein einziger echter bcrypt-Hash fuer das ganze Modul: der Login-Endpunkt muss
# gegen einen echten Hash pruefen, kostet bei Cost 12 aber ~0.3 s pro Aufruf.
PASSWORD_HASH = asyncio.run(hash_password(PASSWORD))
# Fest statt uuid4(): der Wert landet in der Test-Id, und die muss zwischen Laeufen
# stabil bleiben (--last-failed, Flakiness-Historie der CI).
MISSING_DOCUMENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ff")


class _Result:
    """Ersatz fuer das SQLAlchemy-Result; der Flow nutzt nur scalar_one_or_none()."""

    def __init__(self, user: User | None) -> None:
        self._user = user

    def scalar_one_or_none(self) -> User | None:
        return self._user


class FakeDb:
    """AsyncSession-Ersatz, der die zwei SELECTs des Login-Flows beantwortet.

    Aufgeloest wird ueber die gebundenen Parameter des Statements — nach E-Mail
    beim Login, nach Id beim Token-Lookup. Dadurch muss das JWT wirklich das
    richtige Subject tragen, damit die geschuetzte Route antwortet; ein Mock, der
    jeden SELECT mit demselben User beantwortet, wuerde genau das verdecken.

    `User.is_active` steht in beiden Queries, taucht aber als reines
    Spaltenpraedikat ohne Bind-Parameter auf. Es wird deshalb am kompilierten SQL
    erkannt und hier nachgebildet — sonst faellt die Deaktivierungssperre in den
    Tests lautlos weg, obwohl sie in der Anwendung greift.
    """

    def __init__(self, *users: User) -> None:
        self._users = users

    async def execute(self, stmt: Select[Any]) -> _Result:
        compiled = stmt.compile()
        params = compiled.params
        if "email_1" not in params and "id_1" not in params:
            # Lieber laut scheitern als ein irrefuehrendes 401 liefern: die
            # Parameternamen vergibt SQLAlchemy, ein Umbau der Query benennt sie um.
            raise AssertionError(f"FakeDb kennt die Kriterien dieses Statements nicht: {compiled}")

        # Nur die WHERE-Klausel betrachten: `select(User)` fuehrt die Spalte
        # `users.is_active` immer in der SELECT-Liste, am gesamten SQL waere die
        # Erkennung deshalb konstant wahr — und die Sperre wieder ungeprueft.
        enforces_active = "is_active" in str(stmt.whereclause)
        for user in self._users:
            hit = params.get("email_1") == user.email or str(params.get("id_1")) == str(user.id)
            if hit and (user.is_active or not enforces_active):
                return _Result(user)
        return _Result(None)


def make_user(role: str = "learner", is_active: bool = True) -> User:
    return User(
        id=uuid.uuid4(),
        email=EMAIL,
        hashed_password=PASSWORD_HASH,
        role=role,
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def _reset_state() -> Iterator[None]:
    limiter.reset()
    yield
    app.dependency_overrides.clear()
    limiter.reset()


def _client(db: FakeDb) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _login(client: AsyncClient, password: str = PASSWORD) -> Response:
    return await client.post("/auth/login", json={"email": EMAIL, "password": password})


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_login_issues_token_that_opens_protected_route() -> None:
    """AK 1: Happy-Path — nach dem Login ist die geschuetzte Route erreichbar.

    `/auth/me` ist die Route, die das Frontend direkt nach dem Login ruft. Dass der
    Token auch ausserhalb des auth-Routers greift, prueft der E2E-Test gegen den
    laufenden Stack; hier wuerde dafuer nur ein weiterer Fake stehen.
    """
    user = make_user()

    async with _client(FakeDb(user)) as client:
        login = await _login(client)
        assert login.status_code == 200
        token = login.json()["access_token"]

        me = await client.get("/auth/me", headers=_auth(token))
        assert me.status_code == 200
        assert me.json() == {"id": str(user.id), "email": EMAIL, "role": "learner"}


async def test_wrong_password_issues_no_token() -> None:
    """Gegenprobe zum Happy-Path: ohne gueltiges Passwort gibt es keinen Token."""
    async with _client(FakeDb(make_user())) as client:
        r = await _login(client, password="wrong")

        assert r.status_code == 401
        assert "access_token" not in r.json()


@pytest.mark.parametrize("path", ["/auth/me", f"/documents/{MISSING_DOCUMENT_ID}"])
async def test_protected_route_without_token_returns_401(path: str) -> None:
    """Ohne Token antwortet die API auf geschuetzten Routen mit 401.

    Das ist die API-Seite von AK 2. Die Umleitung auf `/login` selbst haengt im
    Frontend am React-State (`ProtectedRoute`) und nicht an diesem Status — sie
    wird in `frontend/src/auth.test.tsx` geprueft, nicht hier.
    """
    async with _client(FakeDb(make_user())) as client:
        r = await client.get(path)

    assert r.status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        # Korrekt geformt und nicht abgelaufen, aber mit fremdem Secret signiert.
        jwt.encode(
            {"sub": str(uuid.uuid4()), "role": "admin"},
            "an-attackers-secret-that-is-long-enough",
            algorithm=settings.jwt_algorithm,
        ),
    ],
    ids=["malformed", "foreign-signature"],
)
async def test_protected_route_with_invalid_token_returns_401(token: str) -> None:
    async with _client(FakeDb(make_user())) as client:
        r = await client.get("/auth/me", headers=_auth(token))

    assert r.status_code == 401


async def test_token_of_unknown_user_returns_401() -> None:
    """Gueltige Signatur genuegt nicht — der User muss beim Zugriff noch existieren."""
    token = create_access_token(str(uuid.uuid4()), "learner")

    async with _client(FakeDb(make_user())) as client:
        r = await client.get("/auth/me", headers=_auth(token))

    assert r.status_code == 401


async def test_deactivated_user_cannot_log_in() -> None:
    """Ein deaktivierter Account bekommt kein Token — sonst blieben Offboardings folgenlos."""
    async with _client(FakeDb(make_user(is_active=False))) as client:
        r = await _login(client)

    assert r.status_code == 401


async def test_token_of_deactivated_user_returns_401() -> None:
    """Die Deaktivierung wirkt sofort und nicht erst, wenn das Token ablaeuft."""
    user = make_user(is_active=False)
    token = create_access_token(str(user.id), user.role)

    async with _client(FakeDb(user)) as client:
        r = await client.get("/auth/me", headers=_auth(token))

    assert r.status_code == 401


async def test_expired_token_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """Die Ablaufzeit (T-06: 1 h) wird beim Zugriff durchgesetzt, nicht nur gesetzt."""
    user = make_user()
    monkeypatch.setattr(settings, "jwt_expire_hours", -1)
    expired = create_access_token(str(user.id), user.role)

    async with _client(FakeDb(user)) as client:
        r = await client.get("/auth/me", headers=_auth(expired))

    assert r.status_code == 401
