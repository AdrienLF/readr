from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Article, Feed, Topic
from ..schemas import ArticleResponse, ArticleListItem, PaginatedArticles
from ..services.fetcher import fetch_reddit_comments

router = APIRouter()


def _article_to_list_item(article: Article) -> ArticleListItem:
    return ArticleListItem(
        id=article.id,
        feed_id=article.feed_id,
        feed_title=article.feed.title if article.feed else None,
        feed_source_type=article.feed.source_type if article.feed else "rss",
        title=article.title,
        url=article.url,
        excerpt=article.excerpt,
        image_url=article.image_url,
        author=article.author,
        published_at=article.published_at,
        is_read=article.is_read,
        is_bookmarked=article.is_bookmarked,
    )


@router.get("", response_model=PaginatedArticles)
async def list_articles(
    topic_id: int | None = None,
    feed_id: int | None = None,
    is_read: bool | None = None,
    is_bookmarked: bool | None = None,
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
        select(Article).options(selectinload(Article.feed)).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    return ArticleResponse(
        id=article.id,
        feed_id=article.feed_id,
        feed_title=article.feed.title if article.feed else None,
        feed_source_type=article.feed.source_type if article.feed else "rss",
        title=article.title,
        url=article.url,
        excerpt=article.excerpt,
        full_content=article.full_content,
        image_url=article.image_url,
        author=article.author,
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        is_read=article.is_read,
        is_bookmarked=article.is_bookmarked,
    )


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
