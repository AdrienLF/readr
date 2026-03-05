import re
import logging
import feedparser
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import Feed, Article, MuteFilter, Rule, Tag
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


async def discover_feeds_from_url(url: str) -> list[dict]:
    """
    Given any URL, return a list of {url, title} dicts for candidate feeds.
    Tries the URL as a direct feed first, then scrapes for <link rel="alternate">.
    """
    # Try as a direct feed
    parsed = feedparser.parse(url)
    if parsed.entries or parsed.feed.get("title"):
        title = parsed.feed.get("title") or url
        return [{"url": url, "title": title}]

    # Fetch HTML and look for feed discovery links
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = await client.get(url)
            html = resp.text
    except Exception:
        return []

    from urllib.parse import urljoin
    patterns = [
        r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*href=["\']([^"\']+)["\']',
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\']',
    ]
    found_urls: list[str] = []
    for pat in patterns:
        found_urls += re.findall(pat, html, re.IGNORECASE)

    results = []
    seen = set()
    for feed_url in found_urls[:5]:
        full_url = urljoin(url, feed_url)
        if full_url in seen:
            continue
        seen.add(full_url)
        p = feedparser.parse(full_url)
        results.append({"url": full_url, "title": p.feed.get("title") or full_url})

    return results


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


def _is_muted(title: str, excerpt: str, filters: list) -> bool:
    """Return True if the article matches any mute filter."""
    text = f"{title} {excerpt or ''}".lower()
    for f in filters:
        try:
            if f.is_regex:
                if re.search(f.pattern, text, re.IGNORECASE):
                    return True
            else:
                if f.pattern.lower() in text:
                    return True
        except Exception:
            pass
    return False


def _matches_condition(article: Article, cond: dict) -> bool:
    """Return True if an article matches a rule condition."""
    field = cond.get("field", "title")
    op = cond.get("op", "contains")
    value = str(cond.get("value", ""))

    raw = ""
    if field == "title":
        raw = article.title or ""
    elif field == "author":
        raw = article.author or ""
    elif field == "feed_id":
        raw = str(article.feed_id)
    elif field == "excerpt":
        raw = article.excerpt or ""

    try:
        if op == "contains":
            return value.lower() in raw.lower()
        elif op == "not_contains":
            return value.lower() not in raw.lower()
        elif op == "equals":
            return raw.lower() == value.lower()
        elif op == "matches":
            return bool(re.search(value, raw, re.IGNORECASE))
    except Exception:
        pass
    return False


def _apply_rules_preview(article: Article, rules: list) -> tuple[bool, list[int], dict]:
    """
    Apply rules in-memory before persisting.
    Returns (is_muted, tag_ids_to_add, field_updates).
    """
    tag_ids = []
    updates = {}
    for rule in rules:
        if not rule.is_active:
            continue
        if not _matches_condition(article, rule.condition):
            continue
        action = rule.action
        if action == "mark_read":
            updates["is_read"] = True
        elif action == "save":
            updates["is_saved"] = True
        elif action == "bookmark":
            updates["is_bookmarked"] = True
        elif action == "mute":
            return True, [], {}
        elif action.startswith("tag:"):
            try:
                tag_ids.append(int(action.split(":", 1)[1]))
            except ValueError:
                pass
    return False, tag_ids, updates


async def fetch_and_store_feed(feed_id: int):
    async with SessionLocal() as db:
        feed = await db.get(Feed, feed_id)
        if not feed:
            return

        # Load mute filters (global + feed-specific)
        filters_result = await db.execute(
            select(MuteFilter).where(
                (MuteFilter.feed_id == None) | (MuteFilter.feed_id == feed_id)
            )
        )
        mute_filters = filters_result.scalars().all()

        # Load active rules
        rules_result = await db.execute(select(Rule).where(Rule.is_active == True))
        rules = rules_result.scalars().all()

        logger.info(f"Fetching feed: {feed.title or feed.url}")
        try:
            parsed = feedparser.parse(feed.url)
            if not parsed.entries and parsed.get("bozo") and not parsed.feed.get("title"):
                raise Exception(str(parsed.get("bozo_exception", "Empty feed / unreachable")))
        except Exception as e:
            feed.last_error = str(e)[:500]
            feed.error_count = (feed.error_count or 0) + 1
            feed.last_fetched = datetime.utcnow()
            await db.commit()
            logger.error(f"Error fetching {feed.url}: {e}")
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

            image_url = _get_rss_image(entry)
            audio_url = _get_audio_url(entry)

            # Apply mute filters
            if _is_muted(title, rss_excerpt or "", mute_filters):
                logger.debug(f"  Muted: {title}")
                continue

            full_content = None
            excerpt = rss_excerpt

            if feed.source_type == "reddit":
                if rss_content and len(rss_content) > 100:
                    full_content = rss_content
                    if not excerpt:
                        import re as _re
                        text = _re.sub(r"<[^>]+>", "", rss_content)
                        excerpt = text[:400] + "…" if len(text) > 400 else text
                else:
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

            # Build article in-memory first so rules can inspect it
            article = Article(
                feed_id=feed_id,
                title=title,
                url=url,
                excerpt=excerpt,
                full_content=full_content,
                image_url=image_url,
                audio_url=audio_url,
                author=author,
                published_at=published_at,
            )

            # Apply rules before persisting
            if rules:
                is_muted, tag_ids, field_updates = _apply_rules_preview(article, rules)
                if is_muted:
                    logger.debug(f"  Rule-muted: {title}")
                    continue
                for k, v in field_updates.items():
                    setattr(article, k, v)
            else:
                tag_ids = []

            db.add(article)

            # Add tags (need flush to get article.id for relationship)
            if tag_ids:
                await db.flush()
                for tag_id in tag_ids:
                    tag = await db.get(Tag, tag_id)
                    if tag:
                        article.tags.append(tag)

            new_count += 1

        feed.last_fetched = datetime.utcnow()
        feed.last_error = None
        feed.error_count = 0
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


def _get_audio_url(entry) -> str | None:
    """Return audio enclosure URL if this is a podcast entry."""
    for enc in getattr(entry, "enclosures", []):
        mime = enc.get("type", "")
        if mime.startswith("audio/"):
            return enc.get("href") or enc.get("url")
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
