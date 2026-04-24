import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


async def test_create_jira_issue():
    from app.integrations.jira.tools import create_jira_issue

    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "PROJ-42"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.jira.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await create_jira_issue("user-1", "PROJ", "Fix bug", "Something is broken")
        assert "PROJ-42" in result


async def test_search_jira():
    from app.integrations.jira.tools import search_jira

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "issues": [
            {"key": "PROJ-1", "fields": {"summary": "Task one", "status": {"name": "Open"}}},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.jira.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await search_jira("user-1", "project = PROJ")
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["key"] == "PROJ-1"


async def test_jira_is_connected():
    from app.integrations.jira import JiraIntegration

    integration = JiraIntegration()
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value='{"access_token": "jira-tok", "cloud_id": "abc"}')
        assert await integration.is_connected("user-1") is True
