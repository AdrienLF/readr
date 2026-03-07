"""API tests for /api/feeds."""
import pytest
from unittest.mock import AsyncMock, patch


# Helper: mock discover_feed to avoid real HTTP
MOCK_FEED_INFO = {
    "url": "https://example.com/feed.rss",
    "title": "Example Feed",
    "description": "A test feed",
    "source_type": "rss",
    "favicon_url": "https://example.com/favicon.ico",
}


@pytest.fixture(autouse=True)
def mock_background_fetch(mocker):
    """Prevent actual feed fetching during API tests."""
    mocker.patch("app.routers.feeds.fetch_and_store_feed", new_callable=AsyncMock)


async def test_list_feeds_empty(client):
    res = await client.get("/api/feeds")
    assert res.status_code == 200
    assert res.json() == []


async def test_add_feed_success(client):
    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        res = await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})

    assert res.status_code == 201
    data = res.json()
    assert data["url"] == "https://example.com/feed.rss"
    assert data["title"] == "Example Feed"
    assert data["source_type"] == "rss"
    assert data["unread_count"] == 0
    assert "id" in data


async def test_add_feed_duplicate_rejected(client):
    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})
        res = await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})

    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()


async def test_add_feed_with_topics(client):
    # Create a topic first
    topic_res = await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    topic_id = topic_res.json()["id"]

    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        res = await client.post(
            "/api/feeds",
            json={"url": "https://example.com/feed.rss", "topic_ids": [topic_id]},
        )

    assert res.status_code == 201
    data = res.json()
    assert len(data["topics"]) == 1
    assert data["topics"][0]["id"] == topic_id


async def test_get_feed_not_found(client):
    res = await client.get("/api/feeds/9999")
    assert res.status_code == 404


async def test_get_feed_by_id(client):
    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        created = await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})
    feed_id = created.json()["id"]

    res = await client.get(f"/api/feeds/{feed_id}")
    assert res.status_code == 200
    assert res.json()["id"] == feed_id


async def test_update_feed_title(client):
    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        created = await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})
    feed_id = created.json()["id"]

    res = await client.put(f"/api/feeds/{feed_id}", json={"title": "Updated Title"})
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"


async def test_update_feed_poll_interval(client):
    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        created = await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})
    feed_id = created.json()["id"]

    res = await client.put(f"/api/feeds/{feed_id}", json={"poll_interval": 1800})
    assert res.status_code == 200
    assert res.json()["poll_interval"] == 1800


async def test_delete_feed(client):
    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        created = await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})
    feed_id = created.json()["id"]

    res = await client.delete(f"/api/feeds/{feed_id}")
    assert res.status_code == 204

    res = await client.get(f"/api/feeds/{feed_id}")
    assert res.status_code == 404


async def test_delete_feed_not_found(client):
    res = await client.delete("/api/feeds/9999")
    assert res.status_code == 404


async def test_refresh_feed(client):
    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        created = await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})
    feed_id = created.json()["id"]

    res = await client.post(f"/api/feeds/{feed_id}/refresh")
    assert res.status_code == 202


async def test_refresh_all_feeds(client):
    with patch("app.routers.feeds.discover_feed", return_value=MOCK_FEED_INFO):
        await client.post("/api/feeds", json={"url": "https://example.com/feed.rss"})

    res = await client.post("/api/feeds/refresh-all")
    assert res.status_code == 202
    assert "1" in res.json()["message"]


async def test_bulk_classify_feeds(client):
    """Bulk classify should discover feeds and return LLM topic assignments."""
    mock_discover = AsyncMock(side_effect=lambda url: {
        "url": url,
        "title": f"Title for {url}",
        "description": "A feed",
        "source_type": "rss",
        "favicon_url": None,
    })
    mock_classify = AsyncMock(return_value=[
        {"url": "https://a.com/feed", "topic_name": "Tech", "is_new_topic": True, "topic_color": "#3b82f6"},
        {"url": "https://b.com/feed", "topic_name": "Tech", "is_new_topic": True, "topic_color": "#3b82f6"},
    ])

    with (
        patch("app.routers.feeds.discover_feed", mock_discover),
        patch("app.routers.feeds.classify_feeds_into_topics", mock_classify),
    ):
        res = await client.post("/api/feeds/bulk-classify", json={
            "urls": ["https://a.com/feed", "https://b.com/feed"],
        })

    assert res.status_code == 200
    data = res.json()
    assert len(data["feeds"]) == 2
    assert data["feeds"][0]["topic_name"] == "Tech"
    assert data["feeds"][0]["title"] == "Title for https://a.com/feed"


async def test_bulk_import_creates_topics_and_feeds(client):
    """Bulk import should create new topics and assign feeds to them."""
    res = await client.post("/api/feeds/bulk-import", json={
        "feeds": [
            {"url": "https://a.com/feed", "topic_name": "Tech", "topic_color": "#3b82f6"},
            {"url": "https://b.com/feed", "topic_name": "Tech", "topic_color": "#3b82f6"},
            {"url": "https://c.com/feed", "topic_name": "Art", "topic_color": "#ec4899"},
        ],
    })

    assert res.status_code == 201
    data = res.json()
    assert data["added"] == 3
    assert data["topics_created"] == 2

    # Verify feeds exist with topics
    feeds_res = await client.get("/api/feeds")
    feeds = feeds_res.json()
    assert len(feeds) == 3
    tech_feeds = [f for f in feeds if any(t["name"] == "Tech" for t in f["topics"])]
    assert len(tech_feeds) == 2


async def test_bulk_import_queues_fetch_only_for_new_feeds(client):
    """Bulk import should queue fetches for only the newly added feeds, not old ones."""
    from app.routers.feeds import fetch_and_store_feed

    # Pre-create an old feed via the old bulk endpoint (title == url pattern)
    await client.post("/api/feeds/bulk", json=[{"url": "https://old.com/feed"}])
    fetch_and_store_feed.reset_mock()

    # Now do a bulk import of new feeds
    res = await client.post("/api/feeds/bulk-import", json={
        "feeds": [
            {"url": "https://x.com/feed", "topic_name": "Tech", "topic_color": "#3b82f6"},
            {"url": "https://y.com/feed", "topic_name": "Art", "topic_color": "#ec4899"},
        ],
    })
    assert res.status_code == 201
    assert res.json()["added"] == 2

    # Should have queued exactly 2 fetches (not 3 — old.com should NOT be re-queued)
    feed_ids_fetched = [c.args[0] for c in fetch_and_store_feed.call_args_list]
    assert len(feed_ids_fetched) == 2


async def test_list_feeds_after_adding(client):
    feeds_info = [
        {**MOCK_FEED_INFO, "url": f"https://example.com/feed{i}.rss", "title": f"Feed {i}"}
        for i in range(3)
    ]
    for info in feeds_info:
        with patch("app.routers.feeds.discover_feed", return_value=info):
            await client.post("/api/feeds", json={"url": info["url"]})

    res = await client.get("/api/feeds")
    assert res.status_code == 200
    assert len(res.json()) == 3
