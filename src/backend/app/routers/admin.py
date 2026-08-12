from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/config", dependencies=[Depends(require_admin)])
async def read_config() -> None:
    """Placeholder so contract and implementation stay symmetric.

    TODO (T-37): read the `config` table. The confidence thresholds already
    have a reader in app/services/config.py (T-24) — this endpoint exposes the
    whole table, not just those.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Noch nicht implementiert (T-37)",
    )


@router.put("/config", dependencies=[Depends(require_admin)])
async def update_config() -> None:
    """Placeholder so contract and implementation stay symmetric.

    TODO (T-37): validate the keys against the known set and write with
    `changed_by`/`changed_at` — that pair is the US-11 audit trail (ERD), so it
    must be filled, not defaulted.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Noch nicht implementiert (T-37)",
    )
