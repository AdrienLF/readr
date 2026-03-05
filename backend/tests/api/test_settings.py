"""API tests for /api/settings."""
import pytest
from unittest.mock import AsyncMock, patch


async def test_get_settings_defaults(client):
    res = await client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["digest_time"] == "07:00"
    assert data["ollama_model"] == "qwen3:8b"
    assert data["fetch_interval"] == 3600


async def test_update_digest_time(client):
    with patch("app.routers.settings.reschedule", new_callable=AsyncMock):
        res = await client.put("/api/settings", json={"digest_time": "08:30"})

    assert res.status_code == 200
    assert res.json()["digest_time"] == "08:30"


async def test_update_ollama_model(client):
    with patch("app.routers.settings.reschedule", new_callable=AsyncMock):
        res = await client.put("/api/settings", json={"ollama_model": "llama3:8b"})

    assert res.status_code == 200
    assert res.json()["ollama_model"] == "llama3:8b"


async def test_update_fetch_interval(client):
    with patch("app.routers.settings.reschedule", new_callable=AsyncMock):
        res = await client.put("/api/settings", json={"fetch_interval": 1800})

    assert res.status_code == 200
    assert res.json()["fetch_interval"] == 1800


async def test_update_settings_partial(client):
    """Partial updates should leave other settings unchanged."""
    with patch("app.routers.settings.reschedule", new_callable=AsyncMock):
        # First set all
        await client.put("/api/settings", json={
            "digest_time": "06:00",
            "ollama_model": "gemma3:8b",
            "fetch_interval": 900,
        })
        # Then update only model
        res = await client.put("/api/settings", json={"ollama_model": "qwen3:8b"})

    data = res.json()
    assert data["digest_time"] == "06:00"   # unchanged
    assert data["ollama_model"] == "qwen3:8b"  # updated
    assert data["fetch_interval"] == 900      # unchanged


async def test_update_settings_calls_reschedule(client):
    """Updating timing settings should trigger scheduler reschedule."""
    with patch("app.routers.settings.reschedule", new_callable=AsyncMock) as mock_reschedule:
        await client.put("/api/settings", json={"digest_time": "09:00", "fetch_interval": 600})

    mock_reschedule.assert_called_once_with(digest_time="09:00", fetch_interval=600)


async def test_settings_persist_across_requests(client):
    with patch("app.routers.settings.reschedule", new_callable=AsyncMock):
        await client.put("/api/settings", json={"ollama_model": "mistral:7b"})

    res = await client.get("/api/settings")
    assert res.json()["ollama_model"] == "mistral:7b"
