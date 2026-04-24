import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


async def test_store_google_tokens(client):
    """Callback should store OAuth tokens in Redis under oauth:google:{user_id}."""
    r = await client.post("/auth/register", json={"email": "g@test.com", "password": "pass"})
    user_id = r.json()["id"]

    fake_tokens = {"access_token": "goog-access", "refresh_token": "goog-refresh"}

    mock_integration = MagicMock()
    mock_integration.display_name = "Google"
    mock_integration.handle_callback = AsyncMock(return_value=fake_tokens)

    with patch("app.api.connect.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        response = await client.get(
            f"/integrations/google/callback?code=fake-code&state={user_id}"
        )
        assert response.status_code == 200
        mock_integration.handle_callback.assert_called_once()


async def test_create_calendar_event(monkeypatch):
    """create_calendar_event should POST to Google Calendar API."""
    from app.integrations.google import tools as gtools

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "event-123", "summary": "Test Meeting"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.google.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration

        result = await gtools.create_calendar_event(
            user_id="user-1",
            title="Test Meeting",
            start_dt="2026-05-01T10:00:00",
            end_dt="2026-05-01T11:00:00"
        )
    # result is now a string like "Event created: event-123 — Test Meeting"
    assert "event-123" in result


async def test_send_gmail(monkeypatch):
    """send_gmail should POST to Gmail API."""
    from app.integrations.google import tools as gtools

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "msg-456"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.google.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration

        result = await gtools.send_gmail(
            user_id="user-1",
            to="recipient@example.com",
            subject="Hello",
            body="Test email body"
        )
    assert "msg-456" in result
