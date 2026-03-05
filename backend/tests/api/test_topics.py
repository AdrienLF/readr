"""API tests for /api/topics."""
import pytest


async def test_list_topics_empty(client):
    res = await client.get("/api/topics")
    assert res.status_code == 200
    assert res.json() == []


async def test_create_topic(client):
    res = await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Tech"
    assert data["color"] == "#6366f1"
    assert data["feed_count"] == 0
    assert "id" in data
    assert "created_at" in data


async def test_create_topic_with_icon(client):
    res = await client.post("/api/topics", json={"name": "Sports", "color": "#22c55e", "icon": "trophy"})
    assert res.status_code == 201
    assert res.json()["icon"] == "trophy"


async def test_list_topics_after_creating(client):
    await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    await client.post("/api/topics", json={"name": "Finance", "color": "#f59e0b"})

    res = await client.get("/api/topics")
    assert res.status_code == 200
    names = [t["name"] for t in res.json()]
    assert "Tech" in names
    assert "Finance" in names


async def test_update_topic(client):
    created = await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    topic_id = created.json()["id"]

    res = await client.put(f"/api/topics/{topic_id}", json={"name": "Technology", "color": "#8b5cf6"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Technology"
    assert data["color"] == "#8b5cf6"


async def test_update_topic_partial(client):
    created = await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    topic_id = created.json()["id"]

    # Only update name
    res = await client.put(f"/api/topics/{topic_id}", json={"name": "Technology"})
    assert res.status_code == 200
    assert res.json()["name"] == "Technology"
    assert res.json()["color"] == "#6366f1"  # unchanged


async def test_update_topic_not_found(client):
    res = await client.put("/api/topics/9999", json={"name": "Ghost"})
    assert res.status_code == 404


async def test_delete_topic(client):
    created = await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    topic_id = created.json()["id"]

    res = await client.delete(f"/api/topics/{topic_id}")
    assert res.status_code == 204

    res = await client.get("/api/topics")
    assert all(t["id"] != topic_id for t in res.json())


async def test_delete_topic_not_found(client):
    res = await client.delete("/api/topics/9999")
    assert res.status_code == 404


async def test_topic_feed_count_updates(client, mocker):
    """feed_count reflects how many feeds are assigned."""
    mocker.patch("app.routers.feeds.fetch_and_store_feed", new_callable=__import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock)

    topic_res = await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    topic_id = topic_res.json()["id"]

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "app.routers.feeds.discover_feed",
        return_value={
            "url": "https://example.com/feed.rss",
            "title": "Test Feed",
            "description": None,
            "source_type": "rss",
            "favicon_url": None,
        },
    ):
        await client.post(
            "/api/feeds",
            json={"url": "https://example.com/feed.rss", "topic_ids": [topic_id]},
        )

    res = await client.get("/api/topics")
    topic = next(t for t in res.json() if t["id"] == topic_id)
    assert topic["feed_count"] == 1
