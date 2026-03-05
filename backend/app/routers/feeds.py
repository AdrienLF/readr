from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Feed, Topic, Article
from ..schemas import FeedCreate, FeedUpdate, FeedResponse
from ..services.fetcher import discover_feed, fetch_and_store_feed

router = APIRouter()


async def _enrich_feed(feed: Feed, db: AsyncSession) -> FeedResponse:
    unread = await db.execute(
        select(func.count(Article.id))
        .where(Article.feed_id == feed.id, Article.is_read == False)
    )
    return FeedResponse(
        **{c.name: getattr(feed, c.name) for c in Feed.__table__.columns},
        unread_count=unread.scalar() or 0,
        topics=[{"id": t.id, "name": t.name, "color": t.color} for t in feed.topics],
    )


@router.get("", response_model=list[FeedResponse])
async def list_feeds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Feed).options(selectinload(Feed.topics)).order_by(Feed.title)
    )
    feeds = result.scalars().all()
    return [await _enrich_feed(f, db) for f in feeds]


@router.post("", response_model=FeedResponse, status_code=201)
async def add_feed(
    payload: FeedCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate
    existing = await db.execute(select(Feed).where(Feed.url == payload.url))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Feed URL already exists")

    info = await discover_feed(payload.url)

    feed = Feed(
        url=info["url"],
        title=info["title"],
        description=info["description"],
        source_type=info["source_type"],
        favicon_url=info["favicon_url"],
    )

    if payload.topic_ids:
        topics = (
            await db.execute(select(Topic).where(Topic.id.in_(payload.topic_ids)))
        ).scalars().all()
        feed.topics = topics

    db.add(feed)
    await db.commit()

    # Re-query with relationships loaded (db.refresh() expires them, causing lazy-load errors)
    result = await db.execute(
        select(Feed).options(selectinload(Feed.topics)).where(Feed.id == feed.id)
    )
    feed = result.scalar_one()

    # Fetch articles in background
    background_tasks.add_task(fetch_and_store_feed, feed.id)

    return await _enrich_feed(feed, db)


@router.get("/{feed_id}", response_model=FeedResponse)
async def get_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Feed).options(selectinload(Feed.topics)).where(Feed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404, "Feed not found")
    return await _enrich_feed(feed, db)


@router.put("/{feed_id}", response_model=FeedResponse)
async def update_feed(feed_id: int, payload: FeedUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Feed).options(selectinload(Feed.topics)).where(Feed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404, "Feed not found")

    if payload.title is not None:
        feed.title = payload.title
    if payload.poll_interval is not None:
        feed.poll_interval = payload.poll_interval
    if payload.topic_ids is not None:
        topics = (
            await db.execute(select(Topic).where(Topic.id.in_(payload.topic_ids)))
        ).scalars().all()
        feed.topics = topics

    await db.commit()
    result = await db.execute(
        select(Feed).options(selectinload(Feed.topics)).where(Feed.id == feed.id)
    )
    feed = result.scalar_one()
    return await _enrich_feed(feed, db)


@router.delete("/{feed_id}", status_code=204)
async def delete_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    feed = await db.get(Feed, feed_id)
    if not feed:
        raise HTTPException(404, "Feed not found")
    await db.delete(feed)
    await db.commit()


@router.post("/{feed_id}/refresh", status_code=202)
async def refresh_feed(
    feed_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    feed = await db.get(Feed, feed_id)
    if not feed:
        raise HTTPException(404, "Feed not found")
    background_tasks.add_task(fetch_and_store_feed, feed_id)
    return {"message": "Refresh queued"}


@router.post("/refresh-all", status_code=202)
async def refresh_all(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    feeds = (await db.execute(select(Feed))).scalars().all()
    for feed in feeds:
        background_tasks.add_task(fetch_and_store_feed, feed.id)
    return {"message": f"Queued {len(feeds)} feeds"}
