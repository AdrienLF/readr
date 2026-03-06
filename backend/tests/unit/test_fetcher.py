"""Unit tests for fetcher.py — pure functions that don't require DB or network."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import app.database as db_module
from app.models import Feed, Article
from app.services.fetcher import fetch_and_store_feed
from app.services.fetcher import (
    detect_source_type,
    normalize_reddit_url,
    _extract_favicon,
    _get_rss_content,
    _get_rss_image,
    _get_rss_excerpt,
    _get_audio_url,
    _parse_comment_tree,
    _parse_date,
    _is_muted,
    _matches_condition,
    _apply_rules_preview,
)


# --- detect_source_type ---

def test_detect_source_type_reddit():
    assert detect_source_type("https://www.reddit.com/r/programming.rss") == "reddit"
    assert detect_source_type("https://reddit.com/r/python") == "reddit"


def test_detect_source_type_rss():
    assert detect_source_type("https://example.com/feed.rss") == "rss"
    assert detect_source_type("https://news.ycombinator.com/rss") == "rss"
    assert detect_source_type("https://rsshub.example.com/bsky/user/foo") == "rss"


# --- normalize_reddit_url ---

def test_normalize_reddit_url_already_rss():
    url = "https://www.reddit.com/r/programming.rss"
    assert normalize_reddit_url(url) == url


def test_normalize_reddit_url_adds_rss():
    assert normalize_reddit_url("https://www.reddit.com/r/programming") == \
        "https://www.reddit.com/r/programming.rss"


def test_normalize_reddit_url_strips_trailing_slash():
    assert normalize_reddit_url("https://www.reddit.com/r/python/") == \
        "https://www.reddit.com/r/python.rss"


# --- _extract_favicon ---

def test_extract_favicon_from_feed_image():
    feed_info = {"image": {"href": "https://example.com/logo.png"}}
    result = _extract_favicon(feed_info, "https://example.com/feed.rss")
    assert result == "https://example.com/logo.png"


def test_extract_favicon_from_domain():
    result = _extract_favicon({}, "https://example.com/feed.rss")
    assert "example.com" in result
    assert "favicon" in result.lower() or "s2" in result


def test_extract_favicon_invalid_url():
    result = _extract_favicon({}, "not-a-url")
    assert result is None


# --- _get_rss_content ---

class MockEntry:
    """Minimal feedparser-style entry: supports both attribute and dict-style access."""
    def get(self, key, default=None):
        return getattr(self, key, default)


def test_get_rss_content_from_content_list():
    entry = MockEntry()
    entry.content = [{"value": "<p>Hello</p>"}]
    assert _get_rss_content(entry) == "<p>Hello</p>"


def test_get_rss_content_from_summary():
    entry = MockEntry()
    entry.content = None
    entry.summary_detail = None
    entry.summary = "Plain text summary"
    assert _get_rss_content(entry) == "Plain text summary"


def test_get_rss_content_empty():
    entry = MockEntry()
    entry.content = None
    entry.summary_detail = None
    entry.summary = None
    assert _get_rss_content(entry) is None


# --- _get_rss_excerpt ---

def test_get_rss_excerpt_strips_html():
    entry = MockEntry()
    entry.summary = "<p>This is a <b>summary</b> with HTML.</p>"
    result = _get_rss_excerpt(entry)
    assert "<p>" not in result
    assert "summary with HTML" in result


def test_get_rss_excerpt_truncates():
    entry = MockEntry()
    entry.summary = "word " * 200  # very long
    result = _get_rss_excerpt(entry)
    assert len(result) <= 405  # 400 chars + ellipsis
    assert result.endswith("…")


def test_get_rss_excerpt_short():
    entry = MockEntry()
    entry.summary = "Short text"
    result = _get_rss_excerpt(entry)
    assert result == "Short text"


def test_get_rss_excerpt_none():
    entry = MockEntry()
    entry.summary = None
    assert _get_rss_excerpt(entry) is None


# --- _get_rss_image ---

def test_get_rss_image_from_media_thumbnail():
    entry = MockEntry()
    entry.media_thumbnail = [{"url": "https://example.com/thumb.jpg"}]
    entry.media_content = None
    entry.enclosures = []
    assert _get_rss_image(entry) == "https://example.com/thumb.jpg"


def test_get_rss_image_from_enclosure():
    entry = MockEntry()
    entry.media_thumbnail = None
    entry.media_content = None
    entry.enclosures = [{"type": "image/jpeg", "href": "https://example.com/img.jpg"}]
    assert _get_rss_image(entry) == "https://example.com/img.jpg"


def test_get_rss_image_none():
    entry = MockEntry()
    entry.media_thumbnail = None
    entry.media_content = None
    entry.enclosures = []
    assert _get_rss_image(entry) is None


# --- _parse_comment_tree ---

def _make_comment(id_, body, score=1, replies=None):
    child = {
        "kind": "t1",
        "data": {
            "id": id_,
            "author": f"user_{id_}",
            "body": body,
            "score": score,
            "created_utc": 1700000000.0,
            "replies": {"data": {"children": replies}} if replies else "",
        },
    }
    return child


def test_parse_comment_tree_flat():
    children = [
        _make_comment("a1", "First comment"),
        _make_comment("a2", "Second comment"),
    ]
    result = _parse_comment_tree(children, depth=0)
    assert len(result) == 2
    assert result[0]["id"] == "a1"
    assert result[0]["body"] == "First comment"
    assert result[0]["depth"] == 0
    assert result[0]["replies"] == []


def test_parse_comment_tree_nested():
    reply = _make_comment("b1", "A reply")
    parent = _make_comment("a1", "Parent comment", replies=[reply])
    result = _parse_comment_tree([parent], depth=0)
    assert len(result) == 1
    assert len(result[0]["replies"]) == 1
    assert result[0]["replies"][0]["id"] == "b1"
    assert result[0]["replies"][0]["depth"] == 1


def test_parse_comment_tree_skips_non_t1():
    children = [
        {"kind": "more", "data": {"children": ["x1"]}},
        _make_comment("a1", "Real comment"),
    ]
    result = _parse_comment_tree(children, depth=0)
    assert len(result) == 1
    assert result[0]["id"] == "a1"


def test_parse_comment_tree_empty():
    assert _parse_comment_tree([], depth=0) == []


# --- _parse_date ---

def test_parse_date_published():
    class E:
        published_parsed = (2024, 1, 15, 10, 30, 0, 0, 0, 0)
        updated_parsed = None
    result = _parse_date(E())
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_parse_date_falls_back_to_updated():
    class E:
        published_parsed = None
        updated_parsed = (2024, 6, 1, 0, 0, 0, 0, 0, 0)
    result = _parse_date(E())
    assert result is not None
    assert result.year == 2024


def test_parse_date_none():
    class E:
        published_parsed = None
        updated_parsed = None
    assert _parse_date(E()) is None


# --- _get_audio_url ---

def test_get_audio_url_found():
    entry = MockEntry()
    entry.enclosures = [{"type": "audio/mpeg", "href": "https://example.com/ep1.mp3"}]
    assert _get_audio_url(entry) == "https://example.com/ep1.mp3"


def test_get_audio_url_uses_url_key():
    entry = MockEntry()
    entry.enclosures = [{"type": "audio/ogg", "url": "https://example.com/ep2.ogg"}]
    assert _get_audio_url(entry) == "https://example.com/ep2.ogg"


def test_get_audio_url_ignores_non_audio():
    entry = MockEntry()
    entry.enclosures = [{"type": "image/jpeg", "href": "https://example.com/img.jpg"}]
    assert _get_audio_url(entry) is None


def test_get_audio_url_empty():
    entry = MockEntry()
    entry.enclosures = []
    assert _get_audio_url(entry) is None


# --- _is_muted ---

class _MockFilter:
    def __init__(self, pattern, is_regex=False):
        self.pattern = pattern
        self.is_regex = is_regex


def test_is_muted_keyword_match():
    filters = [_MockFilter("sponsored")]
    assert _is_muted("This is a Sponsored post", "", filters) is True


def test_is_muted_keyword_no_match():
    filters = [_MockFilter("sponsored")]
    assert _is_muted("Normal article title", "", filters) is False


def test_is_muted_regex_match():
    filters = [_MockFilter(r"^Breaking", is_regex=True)]
    assert _is_muted("Breaking: Something happened", "", filters) is True


def test_is_muted_regex_no_match():
    filters = [_MockFilter(r"^Breaking", is_regex=True)]
    assert _is_muted("Not breaking news", "", filters) is False


def test_is_muted_checks_excerpt():
    filters = [_MockFilter("advertisement")]
    assert _is_muted("Clean title", "This is an advertisement in the body", filters) is True


def test_is_muted_invalid_regex_does_not_crash():
    filters = [_MockFilter(r"[invalid(regex", is_regex=True)]
    assert _is_muted("Some title", "", filters) is False


# --- _matches_condition ---

class _FakeArticle:
    def __init__(self, title="", author="", excerpt="", feed_id=1):
        self.title = title
        self.author = author
        self.excerpt = excerpt
        self.feed_id = feed_id


def test_matches_condition_contains():
    article = _FakeArticle(title="AI is changing everything")
    assert _matches_condition(article, {"field": "title", "op": "contains", "value": "AI"}) is True
    assert _matches_condition(article, {"field": "title", "op": "contains", "value": "blockchain"}) is False


def test_matches_condition_not_contains():
    article = _FakeArticle(title="Python programming")
    assert _matches_condition(article, {"field": "title", "op": "not_contains", "value": "Java"}) is True
    assert _matches_condition(article, {"field": "title", "op": "not_contains", "value": "Python"}) is False


def test_matches_condition_equals():
    article = _FakeArticle(author="John Doe")
    assert _matches_condition(article, {"field": "author", "op": "equals", "value": "john doe"}) is True
    assert _matches_condition(article, {"field": "author", "op": "equals", "value": "Jane"}) is False


def test_matches_condition_regex():
    article = _FakeArticle(title="SPONSORED: Buy this now")
    assert _matches_condition(article, {"field": "title", "op": "matches", "value": r"\bsponsored\b"}) is True


def test_matches_condition_feed_id():
    article = _FakeArticle(feed_id=42)
    assert _matches_condition(article, {"field": "feed_id", "op": "equals", "value": "42"}) is True


# --- _apply_rules_preview ---

class _MockRule:
    def __init__(self, condition, action, is_active=True):
        self.condition = condition
        self.action = action
        self.is_active = is_active


def test_apply_rules_preview_mark_read():
    article = _FakeArticle(title="AI breakthrough")
    rules = [_MockRule({"field": "title", "op": "contains", "value": "AI"}, "mark_read")]
    is_muted, tag_ids, updates = _apply_rules_preview(article, rules)
    assert is_muted is False
    assert updates.get("is_read") is True


def test_apply_rules_preview_save():
    article = _FakeArticle(title="Must read later")
    rules = [_MockRule({"field": "title", "op": "contains", "value": "Must read"}, "save")]
    _, _, updates = _apply_rules_preview(article, rules)
    assert updates.get("is_saved") is True


def test_apply_rules_preview_mute():
    article = _FakeArticle(title="Sponsored content")
    rules = [_MockRule({"field": "title", "op": "contains", "value": "Sponsored"}, "mute")]
    is_muted, _, _ = _apply_rules_preview(article, rules)
    assert is_muted is True


def test_apply_rules_preview_tag():
    article = _FakeArticle(title="Python tutorial")
    rules = [_MockRule({"field": "title", "op": "contains", "value": "Python"}, "tag:7")]
    is_muted, tag_ids, updates = _apply_rules_preview(article, rules)
    assert is_muted is False
    assert 7 in tag_ids


def test_apply_rules_preview_inactive_skipped():
    article = _FakeArticle(title="AI news")
    rules = [_MockRule({"field": "title", "op": "contains", "value": "AI"}, "mark_read", is_active=False)]
    _, _, updates = _apply_rules_preview(article, rules)
    assert "is_read" not in updates


def test_apply_rules_preview_no_match():
    article = _FakeArticle(title="Boring article")
    rules = [_MockRule({"field": "title", "op": "contains", "value": "AI"}, "mark_read")]
    is_muted, tag_ids, updates = _apply_rules_preview(article, rules)
    assert is_muted is False
    assert updates == {}
    assert tag_ids == []


# ---------------------------------------------------------------------------
# Reddit fetch: httpx must be used instead of feedparser's urllib (403 bug)
# ---------------------------------------------------------------------------

REDDIT_ATOM = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>r/synthesizers</title>
  <entry>
    <title>Cool synth post</title>
    <link href="https://www.reddit.com/r/synthesizers/comments/abc123/cool/"/>
    <id>https://www.reddit.com/r/synthesizers/comments/abc123/cool/</id>
    <updated>2026-01-01T10:00:00+00:00</updated>
    <author><name>testuser</name></author>
    <content type="html">&lt;p&gt;This is a long enough content string for the excerpt.&lt;/p&gt;</content>
  </entry>
</feed>
"""


@pytest_asyncio.fixture
async def reddit_db(tmp_path):
    """Isolated DB with a single Reddit feed pre-seeded."""
    db_url = f"sqlite+aiosqlite:///{tmp_path}/reddit.db"
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    orig_engine = db_module.engine
    orig_session = db_module.SessionLocal
    db_module.engine = engine
    db_module.SessionLocal = session_factory

    await db_module.init_db()

    async with session_factory() as session:
        feed = Feed(
            url="https://www.reddit.com/r/synthesizers.rss",
            title="r/synthesizers",
            source_type="reddit",
        )
        session.add(feed)
        await session.commit()
        await session.refresh(feed)
        feed_id = feed.id

    yield feed_id, session_factory

    db_module.engine = orig_engine
    db_module.SessionLocal = orig_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_reddit_feed_fetched_via_httpx_not_feedparser_urllib(reddit_db):
    """
    Regression test for the Reddit 403 bug.

    feedparser's built-in urllib is blocked by Reddit (HTTP 403).
    fetch_and_store_feed must fetch Reddit content via httpx and pass the
    response body to feedparser.parse() — not call feedparser.parse(url).

    The mock makes httpx return a valid Atom feed while feedparser.parse
    raises if it ever receives a URL (simulating what would happen if the
    old urllib path were used).
    """
    feed_id, session_factory = reddit_db

    import feedparser as _fp
    _real_parse = _fp.parse  # capture before patching to avoid infinite recursion

    def feedparser_parse(source, **kwargs):
        # Simulate Reddit 403: fail if called with a URL, succeed on content string
        if isinstance(source, str) and source.startswith("http"):
            mock = MagicMock()
            mock.entries = []
            mock.feed = {}
            mock.bozo = True
            mock.bozo_exception = Exception("HTTP Error 403: Blocked")
            return mock
        return _real_parse(source, **kwargs)

    mock_response = MagicMock()
    mock_response.text = REDDIT_ATOM
    mock_response.raise_for_status = MagicMock()

    mock_httpx_client = AsyncMock()
    mock_httpx_client.__aenter__ = AsyncMock(return_value=mock_httpx_client)
    mock_httpx_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_client.get = AsyncMock(return_value=mock_response)

    with (
        patch("app.services.fetcher.SessionLocal", new=session_factory),
        patch("app.services.fetcher.feedparser.parse", side_effect=feedparser_parse),
        patch("app.services.fetcher.httpx.AsyncClient", return_value=mock_httpx_client),
        patch("app.services.fetcher.fetch_full_content", new_callable=AsyncMock,
              return_value=(None, None, None)),
    ):
        await fetch_and_store_feed(feed_id)

    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(Article).where(Article.feed_id == feed_id))
        articles = result.scalars().all()

    assert len(articles) == 1
    assert articles[0].title == "Cool synth post"
