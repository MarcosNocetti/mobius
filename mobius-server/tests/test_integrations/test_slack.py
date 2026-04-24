import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


async def test_send_slack_message():
    from app.integrations.slack.tools import send_slack_message

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "ts": "1234567890.123456"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.slack.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await send_slack_message("user-1", "#general", "Hello!")
        assert "Message sent" in result
        assert "1234567890" in result


async def test_list_slack_channels():
    from app.integrations.slack.tools import list_slack_channels

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "ok": True,
        "channels": [
            {"id": "C01", "name": "general"},
            {"id": "C02", "name": "random"},
        ],
    }
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.slack.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await list_slack_channels("user-1")
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "general"


async def test_slack_is_connected():
    from app.integrations.slack import SlackIntegration

    integration = SlackIntegration()
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value='{"access_token": "xoxb-tok"}')
        assert await integration.is_connected("user-1") is True
