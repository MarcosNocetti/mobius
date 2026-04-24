import pytest


async def _auth_headers(client) -> dict:
    await client.post("/auth/register", json={"email": "auto@test.com", "password": "pass"})
    r = await client.post("/auth/token", json={"email": "auto@test.com", "password": "pass"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_automation(client):
    headers = await _auth_headers(client)
    response = await client.post("/automations", headers=headers, json={
        "name": "Morning Tweet",
        "description": "Post good morning on Twitter",
        "trigger_type": "cron",
        "trigger_config": {"cron": "0 8 * * *"},
        "script": "async def run(ctx):\n    return 'done'",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Morning Tweet"
    assert data["trigger_config"]["cron"] == "0 8 * * *"
    assert data["status"] == "active"
    assert "id" in data


async def test_list_automations(client):
    headers = await _auth_headers(client)
    await client.post("/automations", headers=headers, json={
        "name": "Daily digest",
        "trigger_config": {"cron": "0 9 * * *"},
        "script": "async def run(ctx):\n    return 'digest'",
    })
    response = await client.get("/automations", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


async def test_delete_automation(client):
    headers = await _auth_headers(client)
    r = await client.post("/automations", headers=headers, json={
        "name": "Weekly report",
        "trigger_config": {"cron": "0 10 * * 1"},
        "script": "async def run(ctx):\n    return 'report'",
    })
    auto_id = r.json()["id"]
    del_resp = await client.delete(f"/automations/{auto_id}", headers=headers)
    assert del_resp.status_code == 204
