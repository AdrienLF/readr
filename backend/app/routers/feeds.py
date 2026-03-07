from datetime import datetime, timezone
from typing import List
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Feed, Topic, Article
from ..schemas import (
    FeedCreate, FeedUpdate, FeedResponse, DiscoveredFeed,
    BulkClassifyRequest, BulkClassifyResponse, ClassifiedFeed,
    BulkImportRequest,
)
from ..services.fetcher import discover_feed, discover_feeds_from_url, fetch_and_store_feed
from ..services.llm import classify_feeds_into_topics

router = APIRouter()


def _compute_health(feed: Feed) -> str:
    if feed.error_count and feed.error_count > 0:
        return "error"
    if not feed.last_fetched:
        return "never"
    lf = feed.last_fetched
    if lf.tzinfo is None:
        lf = lf.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - lf).total_seconds()
    if age > feed.poll_interval * 3:
        return "stale"
    return "ok"


async def _enrich_feed(feed: Feed, db: AsyncSession) -> FeedResponse:
    unread = await db.execute(
        select(func.count(Article.id))
        .where(Article.feed_id == feed.id, Article.is_read == False)
    )
    return FeedResponse(
        **{c.name: getattr(feed, c.name) for c in Feed.__table__.columns},
        unread_count=unread.scalar() or 0,
        health=_compute_health(feed),
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


@router.post("/bulk", status_code=201)
async def bulk_add_feeds(
    payload: list[FeedCreate],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Add many feeds at once, skipping network discovery. URLs are used as-is."""
    existing_result = await db.execute(select(Feed.url))
    existing_urls = {row[0] for row in existing_result.all()}

    added = 0
    skipped = 0
    for item in payload:
        if item.url in existing_urls:
            skipped += 1
            continue
        source_type = "reddit" if "reddit.com" in item.url else "rss"
        feed = Feed(url=item.url, title=item.url, source_type=source_type)
        db.add(feed)
        existing_urls.add(item.url)
        added += 1

    await db.commit()

    # Queue article fetches in background
    result = await db.execute(select(Feed.id).where(Feed.title == Feed.url))
    for (feed_id,) in result.all():
        background_tasks.add_task(fetch_and_store_feed, feed_id)

    return {"added": added, "skipped": skipped}


@router.post("/bulk-classify", response_model=BulkClassifyResponse)
async def bulk_classify_feeds(
    payload: BulkClassifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Discover feed metadata and use LLM to classify them into topics."""
    import asyncio

    # Find already-existing URLs
    existing_result = await db.execute(select(Feed.url))
    existing_urls = {row[0] for row in existing_result.all()}

    # Discover metadata for each URL (with error handling)
    async def safe_discover(url: str) -> dict:
        try:
            return await discover_feed(url)
        except Exception:
            source_type = "reddit" if "reddit.com" in url else "rss"
            return {"url": url, "title": url, "description": None, "source_type": source_type, "favicon_url": None}

    discovered = await asyncio.gather(*[safe_discover(u) for u in payload.urls])

    # Get existing topics
    topics_result = await db.execute(select(Topic))
    existing_topics = [{"name": t.name, "color": t.color} for t in topics_result.scalars().all()]

    # Ask LLM to classify
    feed_data = [{"url": d["url"], "title": d.get("title"), "description": d.get("description")} for d in discovered]
    classifications = await classify_feeds_into_topics(feed_data, existing_topics)

    # Build lookup from LLM results
    classified_by_url = {c["url"]: c for c in classifications}
    existing_topic_names = {t["name"].lower(): t for t in existing_topics}

    result_feeds = []
    for d in discovered:
        c = classified_by_url.get(d["url"])
        if c:
            topic_name = c["topic_name"]
            # Check if topic truly exists (case-insensitive)
            existing_match = existing_topic_names.get(topic_name.lower())
            if existing_match:
                is_new = False
                color = existing_match["color"]
                topic_name = existing_match["name"]  # preserve original casing
            else:
                is_new = c.get("is_new_topic", True)
                color = c.get("topic_color", "#6366f1")
        else:
            topic_name = "Uncategorized"
            is_new = not any(t["name"].lower() == "uncategorized" for t in existing_topics)
            color = "#71717a"

        result_feeds.append(ClassifiedFeed(
            url=d["url"],
            title=d.get("title"),
            description=d.get("description"),
            topic_name=topic_name,
            is_new_topic=is_new,
            topic_color=color,
            already_exists=d["url"] in existing_urls,
        ))

    return BulkClassifyResponse(feeds=result_feeds)


@router.post("/bulk-import", status_code=201)
async def bulk_import_feeds(
    payload: BulkImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Import feeds with topic assignments. Creates new topics as needed."""
    # Find existing URLs
    existing_result = await db.execute(select(Feed.url))
    existing_urls = {row[0] for row in existing_result.all()}

    # Load existing topics by name (case-insensitive)
    topics_result = await db.execute(select(Topic))
    topic_by_name = {t.name.lower(): t for t in topics_result.scalars().all()}

    added = 0
    skipped = 0
    topics_created = 0
    new_feeds = []

    for item in payload.feeds:
        if item.url in existing_urls:
            skipped += 1
            continue

        # Resolve or create topic
        topic = topic_by_name.get(item.topic_name.lower())
        if not topic:
            topic = Topic(name=item.topic_name, color=item.topic_color)
            db.add(topic)
            await db.flush()  # get the ID
            topic_by_name[item.topic_name.lower()] = topic
            topics_created += 1

        source_type = "reddit" if "reddit.com" in item.url else "rss"
        feed = Feed(url=item.url, title=item.url, source_type=source_type)
        feed.topics = [topic]
        db.add(feed)
        new_feeds.append(feed)
        existing_urls.add(item.url)
        added += 1

    await db.flush()  # assign IDs to new feeds
    new_feed_ids = [f.id for f in new_feeds]
    await db.commit()

    # Queue article fetches for newly added feeds only
    for feed_id in new_feed_ids:
        background_tasks.add_task(fetch_and_store_feed, feed_id)

    return {"added": added, "skipped": skipped, "topics_created": topics_created}


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


@router.get("/opml", response_class=Response)
async def export_opml(db: AsyncSession = Depends(get_db)):
    """Export all feeds as an OPML file."""
    result = await db.execute(select(Feed).options(selectinload(Feed.topics)).order_by(Feed.title))
    feeds = result.scalars().all()
    topics_result = await db.execute(select(Topic).order_by(Topic.name))
    topics = topics_result.scalars().all()

    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "Readr Feeds"
    body = ET.SubElement(root, "body")

    # Feeds grouped by topic
    for topic in topics:
        topic_feeds = [f for f in feeds if any(t.id == topic.id for t in f.topics)]
        if not topic_feeds:
            continue
        folder = ET.SubElement(body, "outline", text=topic.name, title=topic.name)
        for feed in topic_feeds:
            ET.SubElement(folder, "outline",
                type="rss", text=feed.title or feed.url,
                title=feed.title or feed.url, xmlUrl=feed.url, htmlUrl=feed.url)

    # Uncategorized feeds
    for feed in feeds:
        if not feed.topics:
            ET.SubElement(body, "outline",
                type="rss", text=feed.title or feed.url,
                title=feed.title or feed.url, xmlUrl=feed.url, htmlUrl=feed.url)

    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    return Response(content=xml_str, media_type="application/xml",
                    headers={"Content-Disposition": "attachment; filename=readr-feeds.opml"})


@router.post("/opml", status_code=202)
async def import_opml(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import feeds from an OPML file."""
    content = await file.read()
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise HTTPException(400, f"Invalid OPML: {e}")

    body = root.find("body")
    if body is None:
        raise HTTPException(400, "OPML missing <body>")

    imported = skipped = 0

    async def _add(xml_url: str, title: str, topic_obj=None):
        nonlocal imported, skipped
        existing = await db.execute(select(Feed).where(Feed.url == xml_url))
        if existing.scalar_one_or_none():
            skipped += 1
            return
        try:
            info = await discover_feed(xml_url)
        except Exception:
            info = {"url": xml_url, "title": title or xml_url,
                    "description": None, "source_type": "rss", "favicon_url": None}
        feed = Feed(url=info["url"], title=info.get("title") or title or xml_url,
                    description=info.get("description"),
                    source_type=info.get("source_type", "rss"),
                    favicon_url=info.get("favicon_url"))
        if topic_obj:
            feed.topics = [topic_obj]
        db.add(feed)
        await db.flush()
        background_tasks.add_task(fetch_and_store_feed, feed.id)
        imported += 1

    for outline in body:
        xml_url = outline.get("xmlUrl")
        title = outline.get("title") or outline.get("text", "")
        if xml_url:
            await _add(xml_url, title)
        else:
            # Folder — find or create topic
            folder_name = outline.get("text") or outline.get("title", "Imported")
            topic_res = await db.execute(select(Topic).where(Topic.name == folder_name))
            topic_obj = topic_res.scalar_one_or_none()
            if not topic_obj:
                topic_obj = Topic(name=folder_name)
                db.add(topic_obj)
                await db.flush()
            for child in outline:
                child_url = child.get("xmlUrl")
                if child_url:
                    await _add(child_url, child.get("title") or child.get("text", ""), topic_obj)

    await db.commit()
    return {"imported": imported, "skipped": skipped}


@router.get("/discover", response_model=List[DiscoveredFeed])
async def discover_feeds(url: str = Query(..., description="Website or feed URL to inspect")):
    """Return candidate feed URLs discovered from a website URL."""
    return await discover_feeds_from_url(url)
