import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


async def test_create_github_issue():
    from app.integrations.github.tools import create_github_issue

    mock_response = MagicMock()
    mock_response.json.return_value = {"number": 42, "title": "Bug report"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.github.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await create_github_issue("user-1", "owner/repo", "Bug report", "Something broke")
        assert "42" in result
        assert "Bug report" in result


async def test_list_github_issues():
    from app.integrations.github.tools import list_github_issues

    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"number": 1, "title": "First issue", "state": "open"},
        {"number": 2, "title": "Second issue", "state": "open"},
    ]
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.github.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await list_github_issues("user-1", "owner/repo")
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["number"] == 1


async def test_github_is_connected():
    from app.integrations.github import GitHubIntegration

    integration = GitHubIntegration()
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value='{"access_token": "tok"}')
        connected = await integration.is_connected("user-1")
        assert connected is True

        mock_redis.get = AsyncMock(return_value=None)
        connected = await integration.is_connected("user-1")
        assert connected is False
