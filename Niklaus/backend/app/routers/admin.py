from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db
from app.models.tables import User

router = APIRouter(prefix="/admin", tags=["admin"])


class ConfigOut(BaseModel):
    config: dict[str, str]


class ConfigUpdate(BaseModel):
    config: dict[str, str]


@router.get("/config", response_model=ConfigOut)
async def get_config(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(text("SELECT key, value FROM config ORDER BY key"))
    return ConfigOut(config={r.key: r.value for r in rows})


@router.put("/config", response_model=ConfigOut)
async def update_config(
    body: ConfigUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    for key, value in body.config.items():
        await db.execute(
            text("UPDATE config SET value = :value, updated_at = now() WHERE key = :key"),
            {"key": key, "value": str(value)},
        )
    await db.commit()
    rows = await db.execute(text("SELECT key, value FROM config ORDER BY key"))
    return ConfigOut(config={r.key: r.value for r in rows})
