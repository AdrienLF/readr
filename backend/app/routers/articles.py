from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, update, case
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..database import get_db
from ..models import Article, Feed, Topic, Tag, Highlight, ArticleSignal, Entity
from ..schemas import (
    ArticleResponse, ArticleListItem, PaginatedArticles, TagBrief,
    HighlightCreate, HighlightResponse, EntityResponse,
)
from ..services.fetcher import fetch_reddit_comments
from ..services.llm import summarize_article as llm_summarize, extract_entities as llm_extract_entities

router = APIRouter()


def _feed_meta(article: Article) -> dict:
    """Computed fields that come from the related feed, not the article columns."""
    return {
        "feed_title": article.feed.title if article.feed else None,
        "feed_source_type": article.feed.source_type if article.feed else "rss",
    }


def _cols(article: Article) -> dict:
    """All ORM column values keyed by column name — picks up new columns automatically."""
    return {c.name: getattr(article, c.name) for c in Article.__table__.columns}


def _article_to_list_item(article: Article) -> ArticleListItem:
    cols = _cols(article)
    return ArticleListItem(
        **{k: v for k, v in cols.items() if k in ArticleListItem.model_fields},
        **_feed_meta(article),
    )


def _article_to_response(article: Article, user_signal: int | None = None) -> ArticleResponse:
    cols = _cols(article)
    return ArticleResponse(
        **{k: v for k, v in cols.items() if k in ArticleResponse.model_fields},
        **_feed_meta(article),
        tags=[TagBrief(id=t.id, name=t.name, color=t.color) for t in (article.tags or [])],
        highlights=[HighlightResponse.model_validate(h) for h in (article.highlights or [])],
        entities=[EntityResponse.model_validate(e) for e in (article.entities or [])],
        user_signal=user_signal,
    )


@router.get("", response_model=PaginatedArticles)
async def list_articles(
    topic_id: int | None = None,
    feed_id: int | None = None,
    is_read: bool | None = None,
    is_bookmarked: bool | None = None,
    is_saved: bool | None = None,
    sort: str = Query("date", pattern="^(date|priority)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Article).options(selectinload(Article.feed))

    if topic_id is not None:
        stmt = (
            stmt.join(Feed, Article.feed_id == Feed.id)
            .join(Feed.topics)
            .where(Topic.id == topic_id)
        )
    if feed_id is not None:
        stmt = stmt.where(Article.feed_id == feed_id)
    if is_read is not None:
        stmt = stmt.where(Article.is_read == is_read)
    if is_bookmarked is not None:
        stmt = stmt.where(Article.is_bookmarked == is_bookmarked)
    if is_saved is not None:
        stmt = stmt.where(Article.is_saved == is_saved)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    if sort == "priority":
        stmt = stmt.order_by(Article.priority_score.desc(), Article.published_at.desc())
    else:
        stmt = stmt.order_by(Article.published_at.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    articles = (await db.execute(stmt)).scalars().all()

    return PaginatedArticles(
        items=[_article_to_list_item(a) for a in articles],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/search", response_model=PaginatedArticles)
async def search_articles(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size

    count_result = await db.execute(
        text("SELECT COUNT(*) FROM articles_fts WHERE articles_fts MATCH :q"),
        {"q": q},
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        text("""
            SELECT articles.*
            FROM articles
            JOIN articles_fts ON articles.id = articles_fts.rowid
            WHERE articles_fts MATCH :q
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """),
        {"q": q, "limit": page_size, "offset": offset},
    )
    rows = result.fetchall()

    # Load full Article objects with feed
    ids = [r[0] for r in rows]
    articles_result = await db.execute(
        select(Article).options(selectinload(Article.feed)).where(Article.id.in_(ids))
    )
    articles_map = {a.id: a for a in articles_result.scalars().all()}
    # Preserve FTS rank order
    articles = [articles_map[i] for i in ids if i in articles_map]

    return PaginatedArticles(
        items=[_article_to_list_item(a) for a in articles],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article)
        .options(
            selectinload(Article.feed),
            selectinload(Article.tags),
            selectinload(Article.highlights),
            selectinload(Article.entities),
        )
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    user_signal = (await db.execute(
        select(ArticleSignal.signal).where(ArticleSignal.article_id == article_id)
    )).scalar_one_or_none()

    return _article_to_response(article, user_signal=user_signal)


@router.patch("/{article_id}/read")
async def mark_read(
    article_id: int,
    is_read: bool = True,
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    article.is_read = is_read
    await db.commit()
    return {"id": article_id, "is_read": is_read}


@router.patch("/{article_id}/bookmark")
async def toggle_bookmark(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    article.is_bookmarked = not article.is_bookmarked
    await db.commit()
    return {"id": article_id, "is_bookmarked": article.is_bookmarked}


@router.get("/{article_id}/comments")
async def get_comments(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).options(selectinload(Article.feed)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    if not article.feed or article.feed.source_type != "reddit":
        raise HTTPException(400, "Comments only available for Reddit articles")

    comments = await fetch_reddit_comments(article.url)
    return {"comments": comments}


class NoteUpdate(BaseModel):
    note: str | None = None


@router.patch("/{article_id}/note")
async def update_note(article_id: int, body: NoteUpdate, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    article.note = body.note
    await db.commit()
    return {"id": article_id, "note": article.note}


@router.patch("/{article_id}/saved")
async def toggle_saved(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    article.is_saved = not article.is_saved
    await db.commit()
    return {"id": article_id, "is_saved": article.is_saved}


@router.post("/{article_id}/summarize")
async def summarize_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).options(selectinload(Article.feed)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    # Return cached summary if available
    if article.summary:
        return {"id": article_id, "summary": article.summary}

    summary = await llm_summarize(article)
    if summary:
        article.summary = summary
        await db.commit()
    return {"id": article_id, "summary": summary}


@router.post("/{article_id}/tags/{tag_id}")
async def add_tag(article_id: int, tag_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).options(selectinload(Article.tags)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")
    if tag not in article.tags:
        article.tags.append(tag)
        await db.commit()
    return {"id": article_id, "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in article.tags]}


@router.delete("/{article_id}/tags/{tag_id}")
async def remove_tag(article_id: int, tag_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).options(selectinload(Article.tags)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    article.tags = [t for t in article.tags if t.id != tag_id]
    await db.commit()
    return {"id": article_id, "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in article.tags]}


# --- Signal (thumbs up / down) ---

class SignalBody(BaseModel):
    signal: int  # 1 = like, -1 = dislike, 0 = remove


@router.post("/{article_id}/signal")
async def signal_article(article_id: int, body: SignalBody, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    if body.signal == 0:
        await db.execute(
            text("DELETE FROM article_signals WHERE article_id = :id"), {"id": article_id}
        )
    else:
        await db.execute(
            sqlite_insert(ArticleSignal)
            .values(article_id=article_id, feed_id=article.feed_id, signal=body.signal)
            .on_conflict_do_update(index_elements=["article_id"], set_={"signal": body.signal})
        )

    # Recompute priority_score for all unread articles from this feed
    likes = (await db.execute(
        select(func.count()).where(ArticleSignal.feed_id == article.feed_id, ArticleSignal.signal == 1)
    )).scalar() or 0
    total = (await db.execute(
        select(func.count()).where(ArticleSignal.feed_id == article.feed_id)
    )).scalar() or 0
    feed_score = (likes / total) if total > 0 else 0.5

    await db.execute(
        update(Article)
        .where(Article.feed_id == article.feed_id, Article.is_read == False)
        .values(priority_score=feed_score)
    )
    await db.commit()
    return {"id": article_id, "signal": body.signal, "feed_score": feed_score}


# --- Highlights ---

@router.get("/{article_id}/highlights", response_model=list[HighlightResponse])
async def list_highlights(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Highlight).where(Highlight.article_id == article_id).order_by(Highlight.created_at)
    )
    return result.scalars().all()


@router.post("/{article_id}/highlights", response_model=HighlightResponse, status_code=201)
async def add_highlight(article_id: int, body: HighlightCreate, db: AsyncSession = Depends(get_db)):
    if not await db.get(Article, article_id):
        raise HTTPException(404, "Article not found")
    h = Highlight(article_id=article_id, text=body.text, note=body.note, color=body.color)
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return h


@router.patch("/{article_id}/highlights/{highlight_id}", response_model=HighlightResponse)
async def update_highlight(article_id: int, highlight_id: int, body: BaseModel, db: AsyncSession = Depends(get_db)):
    h = await db.get(Highlight, highlight_id)
    if not h or h.article_id != article_id:
        raise HTTPException(404, "Highlight not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(h, k, v)
    await db.commit()
    await db.refresh(h)
    return h


@router.delete("/{article_id}/highlights/{highlight_id}", status_code=204)
async def delete_highlight(article_id: int, highlight_id: int, db: AsyncSession = Depends(get_db)):
    h = await db.get(Highlight, highlight_id)
    if not h or h.article_id != article_id:
        raise HTTPException(404, "Highlight not found")
    await db.delete(h)
    await db.commit()


# --- Entity extraction ---

@router.post("/{article_id}/entities", response_model=list[EntityResponse])
async def extract_entities_for_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).options(selectinload(Article.entities)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    # Return cached entities if already extracted
    if article.entities:
        return article.entities

    raw = await llm_extract_entities(article)
    entities = []
    for item in raw:
        name = item.get("name", "").strip()
        etype = item.get("type", "TOPIC").upper()
        if name:
            e = Entity(article_id=article_id, name=name, entity_type=etype)
            db.add(e)
            entities.append(e)

    await db.commit()
    for e in entities:
        await db.refresh(e)
    return entities
