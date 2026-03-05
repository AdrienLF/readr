from datetime import date
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Digest, Topic
from ..schemas import DigestResponse, DigestGenerateRequest
from ..services.llm import generate_all_digests

router = APIRouter()


@router.get("", response_model=list[DigestResponse])
async def list_digests(
    target_date: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Digest).options(selectinload(Digest.topic)).order_by(Digest.generated_at.desc())
    if target_date:
        stmt = stmt.where(Digest.date == target_date)
    else:
        # Default to today
        stmt = stmt.where(Digest.date == date.today().isoformat())

    digests = (await db.execute(stmt)).scalars().all()
    return [
        DigestResponse(
            id=d.id,
            date=d.date,
            topic_id=d.topic_id,
            topic_name=d.topic.name if d.topic else "All Topics",
            content=d.content,
            model_used=d.model_used,
            generated_at=d.generated_at,
        )
        for d in digests
    ]


@router.post("/generate", status_code=202)
async def trigger_digest(
    payload: DigestGenerateRequest,
    background_tasks: BackgroundTasks,
):
    target_date = payload.date or date.today().isoformat()
    background_tasks.add_task(generate_all_digests, target_date, payload.topic_id)
    return {"message": "Digest generation started", "date": target_date}
