import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


async def test_store_google_tokens(client):
    """Callback should store OAuth tokens in Redis under oauth:google:{user_id}."""
    r = await client.post("/auth/register", json={"email": "g@test.com", "password": "pass"})
    user_id = r.json()["id"]

    fake_tokens = {"access_token": "goog-access", "refresh_token": "goog-refresh"}

    with patch("app.integrations.google.exchange_code_for_tokens", new_callable=AsyncMock, return_value=fake_tokens), \
         patch("app.integrations.google.redis_client") as mock_redis:
        mock_redis.set = AsyncMock()
        response = await client.get(
            f"/integrations/google/callback?code=fake-code&state={user_id}"
        )
        assert response.status_code == 200
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert f"oauth:google:{user_id}" in call_args[0]


async def test_create_calendar_event(monkeypatch):
    """create_calendar_event should POST to Google Calendar API."""
    from app.integrations import google as gmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "tok"}')
    monkeypatch.setattr(gmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "event-123", "summary": "Test Meeting"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.google.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http

        result = await gmod.create_calendar_event(
            user_id="user-1",
            title="Test Meeting",
            start_dt="2026-05-01T10:00:00",
            end_dt="2026-05-01T11:00:00"
        )
    assert result["id"] == "event-123"


async def test_send_gmail(monkeypatch):
    """send_gmail should POST to Gmail API."""
    from app.integrations import google as gmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "tok"}')
    monkeypatch.setattr(gmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "msg-456"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.google.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http

        result = await gmod.send_gmail(
            user_id="user-1",
            to="recipient@example.com",
            subject="Hello",
            body="Test email body"
        )
    assert result["id"] == "msg-456"
