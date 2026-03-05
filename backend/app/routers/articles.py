from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Article, Feed, Topic, Tag
from ..schemas import ArticleResponse, ArticleListItem, PaginatedArticles, TagBrief
from ..services.fetcher import fetch_reddit_comments

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


def _article_to_response(article: Article) -> ArticleResponse:
    cols = _cols(article)
    return ArticleResponse(
        **{k: v for k, v in cols.items() if k in ArticleResponse.model_fields},
        **_feed_meta(article),
        tags=[TagBrief(id=t.id, name=t.name, color=t.color) for t in (article.tags or [])],
    )


@router.get("", response_model=PaginatedArticles)
async def list_articles(
    topic_id: int | None = None,
    feed_id: int | None = None,
    is_read: bool | None = None,
    is_bookmarked: bool | None = None,
    is_saved: bool | None = None,
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

    stmt = stmt.order_by(Article.published_at.desc()).offset((page - 1) * page_size).limit(page_size)
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
        .options(selectinload(Article.feed), selectinload(Article.tags))
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    return _article_to_response(article)


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

    from ..services.llm import summarize_article as llm_summarize
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
