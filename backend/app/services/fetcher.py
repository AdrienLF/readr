import re
import logging
import feedparser
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import Feed, Article
from ..database import SessionLocal
from .extractor import fetch_full_content, extract_from_html

logger = logging.getLogger(__name__)

REDDIT_HEADERS = {
    "User-Agent": "RSS-Reader/1.0 (personal; +https://github.com/local/rss-reader)"
}


def detect_source_type(url: str) -> str:
    if "reddit.com" in url:
        return "reddit"
    return "rss"


def normalize_reddit_url(url: str) -> str:
    """Ensure it's an RSS URL."""
    url = url.rstrip("/")
    if not url.endswith(".rss") and not url.endswith(".json"):
        url += ".rss"
    return url


async def discover_feed(url: str) -> dict:
    """
    Given any URL, return {url, title, description, source_type, favicon_url}.
    Handles Reddit normalization and basic feed discovery.
    """
    source_type = detect_source_type(url)
    if source_type == "reddit":
        url = normalize_reddit_url(url)

    parsed = feedparser.parse(url)
    feed_info = parsed.get("feed", {})

    return {
        "url": url,
        "title": feed_info.get("title", url),
        "description": feed_info.get("subtitle") or feed_info.get("description"),
        "source_type": source_type,
        "favicon_url": _extract_favicon(feed_info, url),
    }


def _extract_favicon(feed_info: dict, feed_url: str) -> str | None:
    if feed_info.get("image", {}).get("href"):
        return feed_info["image"]["href"]
    # Derive from domain
    match = re.match(r"https?://[^/]+", feed_url)
    if match:
        return f"https://www.google.com/s2/favicons?domain={match.group()}&sz=32"
    return None


def _parse_date(entry) -> datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        val = getattr(entry, field, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc).replace(tzinfo=None)
            except Exception:
                pass
    return None


async def fetch_and_store_feed(feed_id: int):
    async with SessionLocal() as db:
        feed = await db.get(Feed, feed_id)
        if not feed:
            return

        logger.info(f"Fetching feed: {feed.title or feed.url}")
        try:
            parsed = feedparser.parse(feed.url)
        except Exception as e:
            logger.error(f"feedparser error for {feed.url}: {e}")
            return

        new_count = 0
        for entry in parsed.entries[:50]:  # cap at 50 per fetch
            url = entry.get("link") or entry.get("id")
            if not url:
                continue

            # Skip duplicates
            existing = await db.execute(select(Article).where(Article.url == url))
            if existing.scalar_one_or_none():
                continue

            title = entry.get("title", "Untitled")
            rss_content = _get_rss_content(entry)
            rss_excerpt = _get_rss_excerpt(entry)
            published_at = _parse_date(entry)
            author = entry.get("author") or entry.get("author_detail", {}).get("name")

            # Determine image from RSS first
            image_url = _get_rss_image(entry)

            full_content = None
            excerpt = rss_excerpt

            if feed.source_type == "reddit":
                # For Reddit self-posts, RSS content is already the body
                if rss_content and len(rss_content) > 100:
                    full_content = rss_content
                    if not excerpt:
                        import re as _re
                        text = _re.sub(r"<[^>]+>", "", rss_content)
                        excerpt = text[:400] + "…" if len(text) > 400 else text
                else:
                    # Link post — fetch external article
                    full_content, extracted_excerpt, extracted_image = await fetch_full_content(url)
                    if not excerpt:
                        excerpt = extracted_excerpt
                    if not image_url:
                        image_url = extracted_image
            else:
                full_content, extracted_excerpt, extracted_image = await fetch_full_content(url)
                if not excerpt:
                    excerpt = extracted_excerpt
                if not image_url:
                    image_url = extracted_image

            article = Article(
                feed_id=feed_id,
                title=title,
                url=url,
                excerpt=excerpt,
                full_content=full_content,
                image_url=image_url,
                author=author,
                published_at=published_at,
            )
            db.add(article)
            new_count += 1

        feed.last_fetched = datetime.utcnow()
        await db.commit()
        logger.info(f"  → {new_count} new articles from {feed.title or feed.url}")


def _get_rss_content(entry) -> str | None:
    for field in ("content", "summary_detail"):
        val = getattr(entry, field, None)
        if val:
            if isinstance(val, list) and val:
                return val[0].get("value")
            if hasattr(val, "value"):
                return val.value
    return entry.get("summary")


def _get_rss_excerpt(entry) -> str | None:
    summary = entry.get("summary", "")
    if summary:
        import re
        text = re.sub(r"<[^>]+>", "", summary)
        return text[:400] + "…" if len(text) > 400 else text
    return None


def _get_rss_image(entry) -> str | None:
    # Try media:thumbnail / media:content
    for field in ("media_thumbnail", "media_content"):
        val = getattr(entry, field, None)
        if val and isinstance(val, list) and val:
            return val[0].get("url")
    # Try enclosures
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url")
    return None


async def fetch_reddit_comments(post_url: str) -> list[dict]:
    match = re.search(r"reddit\.com/r/[^/]+/comments/([a-z0-9]+)", post_url)
    if not match:
        return []

    post_id = match.group(1)
    api_url = f"https://www.reddit.com/comments/{post_id}.json?limit=100&sort=top&depth=4"

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=REDDIT_HEADERS) as client:
            response = await client.get(api_url)
            if response.status_code != 200:
                return []
            data = response.json()
    except Exception as e:
        logger.warning(f"Reddit comments fetch failed: {e}")
        return []

    try:
        comments_listing = data[1]["data"]["children"]
        return _parse_comment_tree(comments_listing, depth=0)
    except (IndexError, KeyError, TypeError):
        return []


def _parse_comment_tree(children: list, depth: int) -> list[dict]:
    result = []
    for child in children:
        if child.get("kind") != "t1":
            continue
        d = child["data"]
        comment = {
            "id": d.get("id", ""),
            "author": d.get("author", "[deleted]"),
            "body": d.get("body", ""),
            "score": d.get("score", 0),
            "created_utc": d.get("created_utc", 0),
            "depth": depth,
            "replies": [],
        }
        replies = d.get("replies")
        if isinstance(replies, dict):
            reply_children = replies.get("data", {}).get("children", [])
            comment["replies"] = _parse_comment_tree(reply_children, depth + 1)
        result.append(comment)
    return result
