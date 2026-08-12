from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", dependencies=[Depends(get_current_user)])
async def create_query() -> None:
    """Placeholder so contract and implementation stay symmetric.

    TODO (T-17): retrieval, then T-18 generation and the confidence pipeline.

    Deliberately 501 instead of a plausible-looking stub answer: ADR-008 is
    fail-closed with a 0 % hallucination target, and a fabricated answer with
    fabricated citations is the one thing that must never reach a user. The
    response is declared in openapi.yaml, so the generated client handles it.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Noch nicht implementiert (T-17)",
    )
