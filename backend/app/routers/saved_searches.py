from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models import SavedSearch, ArticleSearchMatch, Article, Feed
from ..services.smart_search import backfill_search, refresh_search_terms

router = APIRouter()


class SavedSearchCreate(BaseModel):
    name: str
    query: str
    is_strict: bool = False


class SavedSearchResponse(BaseModel):
    id: int
    name: str
    query: str
    is_strict: bool = False
    expanded_terms: Optional[list] = None
    backfill_done: bool = False
    match_count: int = 0
    unread_count: int = 0

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SavedSearchResponse])
async def list_saved_searches(db: AsyncSession = Depends(get_db)):
    searches = (await db.execute(select(SavedSearch).order_by(SavedSearch.name))).scalars().all()
    result = []
    for s in searches:
        total = (await db.execute(
            select(func.count()).where(ArticleSearchMatch.search_id == s.id)
        )).scalar() or 0
        unread = (await db.execute(
            select(func.count())
            .select_from(ArticleSearchMatch)
            .join(Article, Article.id == ArticleSearchMatch.article_id)
            .where(ArticleSearchMatch.search_id == s.id, Article.is_read == False)
        )).scalar() or 0
        result.append(SavedSearchResponse(
            id=s.id, name=s.name, query=s.query,
            is_strict=s.is_strict,
            expanded_terms=s.expanded_terms,
            backfill_done=s.backfill_done,
            match_count=total, unread_count=unread,
        ))
    return result


@router.post("", response_model=SavedSearchResponse, status_code=201)
async def create_saved_search(
    payload: SavedSearchCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    search = SavedSearch(name=payload.name, query=payload.query, is_strict=payload.is_strict)
    if payload.is_strict:
        # Strict mode: use user-supplied comma-separated keywords directly
        search.expanded_terms = [t.strip().lower() for t in payload.query.split(",") if t.strip()]
        search.terms_refreshed_at = datetime.now(timezone.utc)
    db.add(search)
    await db.commit()
    await db.refresh(search)
    # Expand terms (AI) + backfill existing articles in background
    background_tasks.add_task(backfill_search, search.id)
    return SavedSearchResponse(
        id=search.id, name=search.name, query=search.query,
        is_strict=search.is_strict, expanded_terms=search.expanded_terms,
    )


@router.delete("/{search_id}", status_code=204)
async def delete_saved_search(search_id: int, db: AsyncSession = Depends(get_db)):
    search = await db.get(SavedSearch, search_id)
    if not search:
        raise HTTPException(404, "Not found")
    await db.delete(search)
    await db.commit()


class SavedSearchUpdate(BaseModel):
    expanded_terms: Optional[list[str]] = None


@router.put("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: int,
    payload: SavedSearchUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    search = await db.get(SavedSearch, search_id)
    if not search:
        raise HTTPException(404, "Not found")
    if payload.expanded_terms is not None:
        search.expanded_terms = payload.expanded_terms
        search.terms_refreshed_at = datetime.now(timezone.utc)
        search.backfill_done = False
    await db.commit()
    await db.refresh(search)
    # Re-backfill with updated terms
    background_tasks.add_task(backfill_search, search.id)
    total = (await db.execute(
        select(func.count()).where(ArticleSearchMatch.search_id == search.id)
    )).scalar() or 0
    unread = (await db.execute(
        select(func.count())
        .select_from(ArticleSearchMatch)
        .join(Article, Article.id == ArticleSearchMatch.article_id)
        .where(ArticleSearchMatch.search_id == search.id, Article.is_read == False)
    )).scalar() or 0
    return SavedSearchResponse(
        id=search.id, name=search.name, query=search.query,
        is_strict=search.is_strict, expanded_terms=search.expanded_terms,
        match_count=total, unread_count=unread,
    )


@router.post("/{search_id}/refresh-terms", status_code=202)
async def refresh_terms(
    search_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    search = await db.get(SavedSearch, search_id)
    if not search:
        raise HTTPException(404, "Not found")
    background_tasks.add_task(backfill_search, search_id)
    return {"message": "Refresh queued"}


@router.get("/{search_id}/articles")
async def get_search_articles(
    search_id: int,
    page: int = 1,
    page_size: int = 30,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    search = await db.get(SavedSearch, search_id)
    if not search:
        raise HTTPException(404, "Not found")

    stmt = (
        select(Article, ArticleSearchMatch.score)
        .join(ArticleSearchMatch, ArticleSearchMatch.article_id == Article.id)
        .where(ArticleSearchMatch.search_id == search_id)
    )
    if unread_only:
        stmt = stmt.where(Article.is_read == False)

    stmt = stmt.order_by(ArticleSearchMatch.score.desc(), Article.published_at.desc())

    total = (await db.execute(
        select(func.count())
        .select_from(ArticleSearchMatch)
        .where(ArticleSearchMatch.search_id == search_id)
    )).scalar() or 0

    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()

    articles = []
    for article, score in rows:
        d = {c.name: getattr(article, c.name) for c in Article.__table__.columns}
        d["search_score"] = round(score, 3)
        articles.append(d)

    return {
        "items": articles,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page * page_size) < total,
    }
