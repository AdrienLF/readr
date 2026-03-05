"""API tests for /api/digests."""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date


async def test_list_digests_empty_today(client):
    res = await client.get("/api/digests")
    assert res.status_code == 200
    assert res.json() == []


async def test_list_digests_by_date(client):
    res = await client.get("/api/digests?target_date=2024-01-15")
    assert res.status_code == 200
    assert res.json() == []


async def test_trigger_digest_generation(client):
    with patch("app.routers.digests.generate_all_digests", new_callable=AsyncMock):
        res = await client.post("/api/digests/generate", json={})

    assert res.status_code == 202
    data = res.json()
    assert data["message"] == "Digest generation started"
    assert "date" in data


async def test_trigger_digest_with_topic(client):
    topic_res = await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    topic_id = topic_res.json()["id"]

    with patch("app.routers.digests.generate_all_digests", new_callable=AsyncMock) as mock_gen:
        res = await client.post("/api/digests/generate", json={"topic_id": topic_id})

    assert res.status_code == 202
    mock_gen.assert_called_once()
    args = mock_gen.call_args
    assert args[0][1] == topic_id  # second positional arg = topic_id


async def test_trigger_digest_with_custom_date(client):
    with patch("app.routers.digests.generate_all_digests", new_callable=AsyncMock):
        res = await client.post("/api/digests/generate", json={"date": "2024-01-15"})

    assert res.status_code == 202
    assert res.json()["date"] == "2024-01-15"


async def test_list_digests_after_generation(client):
    """Digests stored in DB appear in list endpoint."""
    from app.database import SessionLocal
    from app.models import Digest

    async with SessionLocal() as db:
        digest = Digest(
            date="2024-01-15",
            topic_id=None,
            content="1. Overview\n2. Stories",
            model_used="qwen3:8b",
        )
        db.add(digest)
        await db.commit()

    res = await client.get("/api/digests?target_date=2024-01-15")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["date"] == "2024-01-15"
    assert data[0]["content"] == "1. Overview\n2. Stories"
    assert data[0]["model_used"] == "qwen3:8b"
    assert data[0]["topic_name"] == "All Topics"  # topic_id=None


async def test_digest_includes_topic_name(client):
    """Digest with a topic_id shows the topic's name."""
    topic_res = await client.post("/api/topics", json={"name": "Finance", "color": "#f59e0b"})
    topic_id = topic_res.json()["id"]

    from app.database import SessionLocal
    from app.models import Digest

    async with SessionLocal() as db:
        digest = Digest(
            date="2024-01-15",
            topic_id=topic_id,
            content="Finance digest content",
            model_used="qwen3:8b",
        )
        db.add(digest)
        await db.commit()

    res = await client.get("/api/digests?target_date=2024-01-15")
    data = res.json()
    finance_digest = next((d for d in data if d["topic_id"] == topic_id), None)
    assert finance_digest is not None
    assert finance_digest["topic_name"] == "Finance"
