import pytest

async def test_register_creates_user(client):
    response = await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data

async def test_token_returns_jwt(client):
    await client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "pass1234"
    })
    response = await client.post("/auth/token", json={
        "email": "user@example.com",
        "password": "pass1234"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_invalid_credentials_returns_401(client):
    response = await client.post("/auth/token", json={
        "email": "nobody@example.com",
        "password": "wrong"
    })
    assert response.status_code == 401


async def test_store_and_use_api_key(client):
    """User can store an API key and it is passed to the agent engine."""
    import json

    # Register and get token
    await client.post("/auth/register", json={"email": "keyuser@test.com", "password": "pass"})
    r = await client.post("/auth/token", json={"email": "keyuser@test.com", "password": "pass"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Store API key
    resp = await client.put("/auth/api-keys", headers=headers, json={
        "provider": "openai",
        "key": "sk-test-12345"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "stored"

    # Retrieve and verify (via a dedicated endpoint for listing providers)
    list_resp = await client.get("/auth/api-keys", headers=headers)
    assert list_resp.status_code == 200
    providers = list_resp.json()["providers"]
    assert "openai" in providers


async def test_engine_uses_user_key(monkeypatch):
    """run_agent should pick up user-provided key and pass it to LiteLLM."""
    from app.agents.engine import run_agent
    from unittest.mock import patch, MagicMock, AsyncMock

    captured_kwargs = {}

    async def fake_acompletion(**kwargs):
        captured_kwargs.update(kwargs)
        async def gen():
            mock = MagicMock()
            mock.choices = [MagicMock(delta=MagicMock(content="done"))]
            yield mock
        return gen()

    async def noop_token(t):
        pass

    with patch("app.agents.engine.litellm.acompletion", side_effect=fake_acompletion):
        await run_agent(
            message="test",
            model="openai/gpt-4o",
            api_key="sk-user-key",
            tools=[],
            on_token=noop_token,
        )
    assert captured_kwargs.get("api_key") == "sk-user-key"
