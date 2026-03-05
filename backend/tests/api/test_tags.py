"""API tests for /api/tags."""
import pytest


async def test_list_tags_empty(client):
    res = await client.get("/api/tags")
    assert res.status_code == 200
    assert res.json() == []


async def test_create_tag(client):
    res = await client.post("/api/tags", json={"name": "Python", "color": "#3b82f6"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Python"
    assert data["color"] == "#3b82f6"
    assert "id" in data
    assert "created_at" in data


async def test_create_tag_default_color(client):
    res = await client.post("/api/tags", json={"name": "NoColor"})
    assert res.status_code == 201
    assert res.json()["color"] == "#6366f1"


async def test_create_duplicate_tag_fails(client):
    await client.post("/api/tags", json={"name": "Unique"})
    res = await client.post("/api/tags", json={"name": "Unique"})
    assert res.status_code == 409


async def test_list_tags_after_create(client):
    await client.post("/api/tags", json={"name": "A"})
    await client.post("/api/tags", json={"name": "B"})

    res = await client.get("/api/tags")
    assert res.status_code == 200
    names = [t["name"] for t in res.json()]
    assert "A" in names
    assert "B" in names


async def test_delete_tag(client):
    create_res = await client.post("/api/tags", json={"name": "ToDelete"})
    tag_id = create_res.json()["id"]

    res = await client.delete(f"/api/tags/{tag_id}")
    assert res.status_code == 204

    # Confirm gone
    tags = (await client.get("/api/tags")).json()
    assert not any(t["id"] == tag_id for t in tags)


async def test_delete_tag_not_found(client):
    res = await client.delete("/api/tags/9999")
    assert res.status_code == 404
