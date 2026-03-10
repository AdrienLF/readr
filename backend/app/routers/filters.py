import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import MuteFilter
from ..schemas import MuteFilterCreate, MuteFilterResponse

router = APIRouter()


@router.get("", response_model=list[MuteFilterResponse])
async def list_filters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MuteFilter).order_by(MuteFilter.created_at))
    return result.scalars().all()


def _is_safe_regex(pattern: str) -> bool:
    """Reject regex patterns likely to cause catastrophic backtracking."""
    # Block nested quantifiers like (a+)+, (a*)*,  (a{2,})+
    if re.search(r'\([^)]*[+*]\)[+*]', pattern):
        return False
    if re.search(r'\([^)]*\{[0-9,]+\}\)[+*]', pattern):
        return False
    return True


@router.post("", response_model=MuteFilterResponse, status_code=201)
async def create_filter(payload: MuteFilterCreate, db: AsyncSession = Depends(get_db)):
    if payload.is_regex:
        import re
        try:
            re.compile(payload.pattern)
        except re.error as e:
            raise HTTPException(400, f"Invalid regex: {e}")
        if not _is_safe_regex(payload.pattern):
            raise HTTPException(400, "Regex pattern rejected: nested quantifiers can cause excessive backtracking")
    f = MuteFilter(**payload.model_dump())
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


@router.delete("/{filter_id}", status_code=204)
async def delete_filter(filter_id: int, db: AsyncSession = Depends(get_db)):
    f = await db.get(MuteFilter, filter_id)
    if not f:
        raise HTTPException(404, "Filter not found")
    await db.delete(f)
    await db.commit()
