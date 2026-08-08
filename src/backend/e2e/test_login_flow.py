"""T-09: Login-Flow end-to-end gegen den laufenden Stack.

Diese Datei liegt bewusst ausserhalb von `tests/` (`testpaths = ["tests"]` in
pyproject.toml) und laeuft daher nicht in der Unit-Suite mit, sondern nur ueber
`make e2e` bzw. den `e2e`-Job der CI. Gesprochen wird ueber nginx mit dem echten
API-Container und der echten Datenbank — nichts ist gemockt.

Damit sind genau die Nahtstellen abgedeckt, die `tests/` prinzipbedingt nicht
sieht:
  * das `/api`-Rewrite von nginx (Frontend ruft `/api/auth/login`, FastAPI hoert
    auf `/auth/login`),
  * der SPA-Fallback (ein Reload auf `/login` muss `index.html` liefern, sonst
    endet die Umleitung aus AK 2 im 404),
  * der echte bcrypt-Hash aus der `users`-Tabelle statt eines Fixtures.

Vorbedingung: laufender Stack mit geseedeten Usern (`make up && make seed`).
"""

import os
import uuid
from collections.abc import Iterator

import httpx
import pytest

# Default ist der Servicename im edge-Netz: der Test laeuft im api-Container und
# erreicht nginx dort unter http://webapp — lokal wie in der CI identisch.
BASE_URL = os.environ.get("E2E_BASE_URL", "http://webapp")

# Seed-User aus seed_users.py. Die Credentials sind Wegwerf-Zugaenge eines
# Wegwerf-Stacks (CI-Container bzw. lokale Entwicklungsumgebung).
EMAIL = "lara@learnflow.local"
PASSWORD = "changeme6"
ROLE = "learner"

# Fest statt uuid4(): der Wert landet in der Test-Id, und die muss zwischen Laeufen
# stabil bleiben (--last-failed, Flakiness-Historie der CI).
MISSING_DOCUMENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ff")


@pytest.fixture(scope="module")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def login(client: httpx.Client) -> httpx.Response:
    """Der einzige Login des Moduls.

    /auth/login ist auf 5 Versuche pro Minute und IP limitiert (app/limiter.py),
    und der Zaehler lebt im laufenden api-Prozess — er ueberdauert also den
    Testlauf. Bei einem Login pro Lauf sind fuenf Laeufe pro Minute moeglich; wer
    hier weitere Logins ergaenzt, verkuerzt das entsprechend.
    """
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 429:
        pytest.fail(
            "Rate-Limit erschoepft (5 Logins/Minute/IP). Das Fenster ueberlebt den "
            "Testlauf: eine Minute warten oder `docker compose restart api`."
        )
    return r


@pytest.fixture(scope="module")
def token(login: httpx.Response) -> str:
    assert login.status_code == 200, login.text
    return str(login.json()["access_token"])


def test_root_serves_the_spa(client: httpx.Client) -> None:
    r = client.get("/")

    assert r.status_code == 200
    assert '<div id="root">' in r.text


def test_deep_link_to_login_serves_the_spa(client: httpx.Client) -> None:
    """Ein Reload auf /login darf nicht im 404 landen — sonst fuehrt die Umleitung
    aus AK 2 in Produktion ins Leere."""
    r = client.get("/login")

    assert r.status_code == 200
    assert '<div id="root">' in r.text


def test_login_returns_token_and_role(login: httpx.Response) -> None:
    """AK 1, erster Teil: Login ueber nginx gegen die echte users-Tabelle."""
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["access_token"]
    assert body["role"] == ROLE


def test_token_opens_protected_route(client: httpx.Client, token: str) -> None:
    """AK 1, zweiter Teil: mit dem Token ist die geschuetzte Route erreichbar."""
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200
    assert r.json()["email"] == EMAIL
    assert r.json()["role"] == ROLE


def test_token_is_accepted_outside_the_auth_router(client: httpx.Client, token: str) -> None:
    """404 statt 401: die Authentifizierung greift, nur das Dokument gibt es nicht.

    Zeigt, dass Token und /api-Rewrite auch fuer Fachrouten funktionieren und
    nicht nur fuer die Selbstauskunft des auth-Routers.
    """
    r = client.get(
        f"/api/documents/{MISSING_DOCUMENT_ID}", headers={"Authorization": f"Bearer {token}"}
    )

    assert r.status_code == 404


@pytest.mark.parametrize("path", ["/api/auth/me", f"/api/documents/{MISSING_DOCUMENT_ID}"])
def test_protected_route_without_token_returns_401(client: httpx.Client, path: str) -> None:
    """Ohne Token antwortet die API auf geschuetzten Routen mit 401.

    Das ist die API-Seite von AK 2. Die Umleitung auf `/login` haengt im Frontend
    am React-State (`ProtectedRoute`) und nicht an diesem Status — sie wird in
    `frontend/src/auth.test.tsx` geprueft, nicht hier.
    """
    r = client.get(path)

    assert r.status_code == 401
