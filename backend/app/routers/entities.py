from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..database import get_db
from ..models import Entity
from ..schemas import TrendingEntity

router = APIRouter()


@router.get("/trending", response_model=list[TrendingEntity])
async def trending_entities(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).replace(tzinfo=None)
    result = await db.execute(
        select(Entity.name, Entity.entity_type, func.count(Entity.id).label("count"))
        .where(Entity.created_at >= since)
        .group_by(Entity.name, Entity.entity_type)
        .order_by(func.count(Entity.id).desc())
        .limit(limit)
    )
    return [TrendingEntity(name=r.name, entity_type=r.entity_type, count=r.count) for r in result.all()]
