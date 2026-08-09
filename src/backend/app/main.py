from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response

from app.limiter import limiter
from app.routers import auth, documents

app = FastAPI(title="LearnFlow API")
app.state.limiter = limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """429 body with a `detail` key, matching the Error schema in openapi.yaml.

    slowapi's built-in handler returns `{"error": ...}`, which no other error response
    of this API uses. Header injection is what the built-in handler does too.
    """
    response = JSONResponse(
        {"detail": f"Rate limit exceeded: {exc.detail}"},
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
