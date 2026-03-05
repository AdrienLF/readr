from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Setting
from ..schemas import SettingsUpdate, SettingsResponse
from ..services.scheduler import reschedule

router = APIRouter()


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Setting))).scalars().all()
    data = {r.key: r.value for r in rows}
    return SettingsResponse(
        digest_time=data.get("digest_time", "07:00"),
        ollama_model=data.get("ollama_model", "qwen3:8b"),
        fetch_interval=int(data.get("fetch_interval", "3600")),
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(payload: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    updates: dict[str, str] = {}

    if payload.digest_time is not None:
        updates["digest_time"] = payload.digest_time
    if payload.ollama_model is not None:
        updates["ollama_model"] = payload.ollama_model
    if payload.fetch_interval is not None:
        updates["fetch_interval"] = str(payload.fetch_interval)

    for key, value in updates.items():
        row = await db.get(Setting, key)
        if row:
            row.value = value
        else:
            db.add(Setting(key=key, value=value))

    await db.commit()

    # Reschedule jobs if timing changed
    await reschedule(
        digest_time=payload.digest_time,
        fetch_interval=payload.fetch_interval,
    )

    return await get_settings(db)
