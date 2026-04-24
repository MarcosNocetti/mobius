import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


async def test_send_teams_message():
    from app.integrations.teams.tools import send_teams_message

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "msg-001"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.teams.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await send_teams_message("user-1", "chat-123", "Hello Teams!")
        assert "msg-001" in result


async def test_list_teams():
    from app.integrations.teams.tools import list_teams

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "value": [
            {"id": "team-1", "displayName": "Engineering"},
            {"id": "team-2", "displayName": "Marketing"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.teams.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await list_teams("user-1")
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["displayName"] == "Engineering"


async def test_teams_is_connected():
    from app.integrations.teams import TeamsIntegration

    integration = TeamsIntegration()
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value='{"access_token": "az-tok"}')
        assert await integration.is_connected("user-1") is True
