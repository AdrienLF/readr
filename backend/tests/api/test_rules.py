"""API tests for /api/rules."""
import pytest


_VALID_RULE = {
    "name": "Auto-save AI articles",
    "condition": {"field": "title", "op": "contains", "value": "AI"},
    "action": "save",
}


async def test_list_rules_empty(client):
    res = await client.get("/api/rules")
    assert res.status_code == 200
    assert res.json() == []


async def test_create_rule(client):
    res = await client.post("/api/rules", json=_VALID_RULE)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Auto-save AI articles"
    assert data["condition"] == {"field": "title", "op": "contains", "value": "AI"}
    assert data["action"] == "save"
    assert data["is_active"] is True
    assert "id" in data


async def test_create_rule_all_actions(client):
    for action in ("mark_read", "save", "bookmark", "mute"):
        res = await client.post("/api/rules", json={
            "name": f"Rule {action}",
            "condition": {"field": "title", "op": "contains", "value": "x"},
            "action": action,
        })
        assert res.status_code == 201, f"Failed for action={action}"


async def test_create_rule_tag_action(client):
    res = await client.post("/api/rules", json={
        "name": "Tag rule",
        "condition": {"field": "author", "op": "equals", "value": "Alice"},
        "action": "tag:42",
    })
    assert res.status_code == 201
    assert res.json()["action"] == "tag:42"


async def test_create_rule_invalid_field(client):
    res = await client.post("/api/rules", json={
        "name": "Bad field",
        "condition": {"field": "url", "op": "contains", "value": "x"},
        "action": "save",
    })
    assert res.status_code == 422


async def test_create_rule_invalid_op(client):
    res = await client.post("/api/rules", json={
        "name": "Bad op",
        "condition": {"field": "title", "op": "starts_with", "value": "x"},
        "action": "save",
    })
    assert res.status_code == 422


async def test_create_rule_invalid_action(client):
    res = await client.post("/api/rules", json={
        "name": "Bad action",
        "condition": {"field": "title", "op": "contains", "value": "x"},
        "action": "unknown_action",
    })
    assert res.status_code == 422


async def test_update_rule_toggle_active(client):
    create_res = await client.post("/api/rules", json=_VALID_RULE)
    rule_id = create_res.json()["id"]

    res = await client.patch(f"/api/rules/{rule_id}", json={"is_active": False})
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    res2 = await client.patch(f"/api/rules/{rule_id}", json={"is_active": True})
    assert res2.json()["is_active"] is True


async def test_update_rule_name_and_condition(client):
    create_res = await client.post("/api/rules", json=_VALID_RULE)
    rule_id = create_res.json()["id"]

    res = await client.patch(f"/api/rules/{rule_id}", json={
        "name": "Updated name",
        "condition": {"field": "author", "op": "equals", "value": "Bob"},
    })
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Updated name"
    assert data["condition"]["field"] == "author"
    # action unchanged
    assert data["action"] == "save"


async def test_update_rule_not_found(client):
    res = await client.patch("/api/rules/9999", json={"is_active": False})
    assert res.status_code == 404


async def test_delete_rule(client):
    create_res = await client.post("/api/rules", json=_VALID_RULE)
    rule_id = create_res.json()["id"]

    res = await client.delete(f"/api/rules/{rule_id}")
    assert res.status_code == 204

    rules = (await client.get("/api/rules")).json()
    assert not any(r["id"] == rule_id for r in rules)


async def test_delete_rule_not_found(client):
    res = await client.delete("/api/rules/9999")
    assert res.status_code == 404


async def test_list_rules_after_create(client):
    await client.post("/api/rules", json=_VALID_RULE)
    await client.post("/api/rules", json={**_VALID_RULE, "name": "Rule 2", "action": "bookmark"})

    res = await client.get("/api/rules")
    assert len(res.json()) == 2
