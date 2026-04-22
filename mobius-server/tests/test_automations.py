import pytest


async def _auth_headers(client) -> dict:
    await client.post("/auth/register", json={"email": "auto@test.com", "password": "pass"})
    r = await client.post("/auth/token", json={"email": "auto@test.com", "password": "pass"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_automation(client):
    headers = await _auth_headers(client)
    response = await client.post("/automations", headers=headers, json={
        "prompt": "Post good morning on Twitter",
        "cron_expr": "0 8 * * *",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["prompt"] == "Post good morning on Twitter"
    assert data["cron_expr"] == "0 8 * * *"
    assert data["active"] is True
    assert "id" in data


async def test_list_automations(client):
    headers = await _auth_headers(client)
    await client.post("/automations", headers=headers, json={
        "prompt": "Daily digest", "cron_expr": "0 9 * * *"
    })
    response = await client.get("/automations", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


async def test_delete_automation(client):
    headers = await _auth_headers(client)
    r = await client.post("/automations", headers=headers, json={
        "prompt": "Weekly report", "cron_expr": "0 10 * * 1"
    })
    auto_id = r.json()["id"]
    del_resp = await client.delete(f"/automations/{auto_id}", headers=headers)
    assert del_resp.status_code == 204
