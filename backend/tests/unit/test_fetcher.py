"""Unit tests for fetcher.py — pure functions that don't require DB or network."""
import pytest
from app.services.fetcher import (
    detect_source_type,
    normalize_reddit_url,
    _extract_favicon,
    _get_rss_content,
    _get_rss_image,
    _get_rss_excerpt,
    _parse_comment_tree,
    _parse_date,
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
    pass


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
