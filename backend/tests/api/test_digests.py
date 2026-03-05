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


async def test_trigger_digest_generation_synchronous(client):
    """generate endpoint now returns the generated digests synchronously."""
    with patch("app.routers.digests.generate_all_digests", new_callable=AsyncMock):
        res = await client.post("/api/digests/generate", json={})

    assert res.status_code == 200
    # No digests were actually created (mock), so returns empty list
    assert isinstance(res.json(), list)


async def test_trigger_digest_with_topic(client):
    topic_res = await client.post("/api/topics", json={"name": "Tech", "color": "#6366f1"})
    topic_id = topic_res.json()["id"]

    with patch("app.routers.digests.generate_all_digests", new_callable=AsyncMock) as mock_gen:
        res = await client.post("/api/digests/generate", json={"topic_id": topic_id})

    assert res.status_code == 200
    mock_gen.assert_called_once()
    call_args = mock_gen.call_args
    assert call_args[0][1] == topic_id  # second positional arg = topic_id


async def test_trigger_digest_with_custom_date(client):
    with patch("app.routers.digests.generate_all_digests", new_callable=AsyncMock):
        res = await client.post("/api/digests/generate", json={"date": "2024-01-15"})

    assert res.status_code == 200
    # Should return digests for that date (empty since mock didn't create any)
    assert isinstance(res.json(), list)


async def test_trigger_digest_generation_error_surfaces(client):
    """If Ollama fails, the endpoint returns 500 with the error message."""
    with patch(
        "app.routers.digests.generate_all_digests",
        new_callable=AsyncMock,
        side_effect=Exception("Connection refused"),
    ):
        res = await client.post("/api/digests/generate", json={})

    assert res.status_code == 500
    assert "Connection refused" in res.json()["detail"]


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
    assert data[0]["topic_name"] == "All Topics"


async def test_digest_includes_topic_name(client):
    topic_res = await client.post("/api/topics", json={"name": "Finance", "color": "#f59e0b"})
    topic_id = topic_res.json()["id"]

    from app.database import SessionLocal
    from app.models import Digest

    async with SessionLocal() as db:
        digest = Digest(
            date="2024-01-15",
            topic_id=topic_id,
            content="Finance digest",
            model_used="qwen3:8b",
        )
        db.add(digest)
        await db.commit()

    res = await client.get("/api/digests?target_date=2024-01-15")
    data = res.json()
    finance = next((d for d in data if d["topic_id"] == topic_id), None)
    assert finance is not None
    assert finance["topic_name"] == "Finance"


async def test_generate_returns_newly_created_digests(client):
    """After generation, the endpoint returns the digests it just created."""
    from app.database import SessionLocal
    from app.models import Digest

    target_date = "2024-06-01"

    async def fake_generate(date, topic_id):
        async with SessionLocal() as db:
            db.add(Digest(
                date=date,
                topic_id=None,
                content="Generated content",
                model_used="qwen3:8b",
            ))
            await db.commit()

    with patch("app.routers.digests.generate_all_digests", side_effect=fake_generate):
        res = await client.post("/api/digests/generate", json={"date": target_date})

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["content"] == "Generated content"
    assert data[0]["date"] == target_date
