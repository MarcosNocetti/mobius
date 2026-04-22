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
