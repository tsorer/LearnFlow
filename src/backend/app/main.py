from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response

from app.config import settings
from app.limiter import limiter
from app.routers import admin, auth, documents, feedback, query, quiz

# Passing None removes the route entirely rather than hiding it, so there is no
# unauthenticated endpoint left to find. app.openapi() keeps working in-process,
# which is what the spec-conformance check in tests/test_rbac.py builds on.
#
# root_path is what makes the enabled docs actually usable: the API is only
# reachable through nginx's `location /api/`, which strips the prefix before
# proxying. Routing therefore matches the stripped path, but every URL the app
# hands to a browser — Swagger's reference to its own spec above all — has to
# carry /api again, or it lands in the SPA fallback instead.
_docs = settings.expose_api_docs
app = FastAPI(
    title="LearnFlow API",
    root_path="/api",
    openapi_url="/openapi.json" if _docs else None,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
)
app.state.limiter = limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """429 body with a `detail` key, matching the Error schema in openapi.yaml.

    slowapi's built-in handler returns `{"error": ...}`, which no other error response
    of this API uses. Header injection is what the built-in handler does too.

    The text is German and free of the limit expression, like every other message
    this API shows a user; the machine-readable part travels in the headers the
    line below injects. `exc.detail` reads "10 per 1 minute" — useful in a log,
    not in a sentence someone is meant to act on.
    """
    response = JSONResponse(
        {"detail": "Zu viele Anfragen. Bitte warte einen Moment und versuche es erneut."},
        status_code=429,
    )
    return limiter._inject_headers(response, request.state.view_rate_limit)


# The handler is narrowly typed for RateLimitExceeded; Starlette's signature expects
# the general Exception type — safe, dispatch is by the registered class.
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(feedback.router)
app.include_router(admin.router)
app.include_router(quiz.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe for the Docker healthcheck — declared in openapi.yaml
    with `security: []`, because the check runs without credentials.
    """
    return {"status": "ok"}
