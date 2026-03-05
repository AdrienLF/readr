from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Digest, Topic
from ..schemas import DigestResponse, DigestGenerateRequest
from ..services.llm import generate_all_digests

router = APIRouter()


def _fmt(d: Digest) -> DigestResponse:
    return DigestResponse(
        id=d.id,
        date=d.date,
        topic_id=d.topic_id,
        topic_name=d.topic.name if d.topic else "All Topics",
        content=d.content,
        model_used=d.model_used,
        generated_at=d.generated_at,
    )


@router.get("", response_model=list[DigestResponse])
async def list_digests(
    target_date: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Digest).options(selectinload(Digest.topic)).order_by(Digest.generated_at.desc())
    stmt = stmt.where(Digest.date == (target_date or date.today().isoformat()))
    digests = (await db.execute(stmt)).scalars().all()
    return [_fmt(d) for d in digests]


@router.post("/generate", response_model=list[DigestResponse])
async def trigger_digest(
    payload: DigestGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate digest synchronously and return the results (or raise on error)."""
    target_date = payload.date or date.today().isoformat()

    try:
        await generate_all_digests(target_date, payload.topic_id)
    except Exception as e:
        raise HTTPException(500, f"Digest generation failed: {e}")

    # Return the freshly generated digests
    stmt = (
        select(Digest)
        .options(selectinload(Digest.topic))
        .where(Digest.date == target_date)
        .order_by(Digest.generated_at.desc())
    )
    if payload.topic_id is not None:
        stmt = stmt.where(Digest.topic_id == payload.topic_id)

    digests = (await db.execute(stmt)).scalars().all()
    return [_fmt(d) for d in digests]
