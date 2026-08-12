"""Swagger UI, ReDoc and /openapi.json must not be public by default.

FastAPI serves all three without authentication, and they describe the complete
API surface. For a platform holding internal documents that is a deployment
decision, not a default — so the flag is off unless someone opts in, and these
tests pin both halves of that: the default itself, and the wiring that turns it
into actual routes.
"""

from app.config import Settings, settings
from app.main import app


def test_docs_are_off_by_default() -> None:
    """A deployment that sets nothing must not publish the docs."""
    assert Settings.model_fields["expose_api_docs"].default is False


def test_routes_follow_the_flag() -> None:
    """The three URLs are wired to the flag, not hardcoded.

    Asserted as an equivalence so this holds under either configuration — a
    developer with EXPOSE_API_DOCS=true in their .env sees the same guarantee.

    That the routes really appear and disappear with it — not merely the
    attributes — is checked against the served route table in
    tests/test_rbac.py::test_only_api_routes_and_known_framework_routes_are_served.
    """
    exposed = settings.expose_api_docs
    assert (app.openapi_url is not None) is exposed
    assert (app.docs_url is not None) is exposed
    assert (app.redoc_url is not None) is exposed


def test_docs_urls_carry_the_proxy_prefix() -> None:
    """Enabled docs have to be usable, not just present.

    nginx serves the API under /api/ and strips the prefix before proxying, so
    Swagger's own reference to /openapi.json would miss the location block and
    land in the SPA fallback. root_path is what puts the prefix back.
    """
    assert app.root_path == "/api"

