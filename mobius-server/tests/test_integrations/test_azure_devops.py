import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


async def test_create_work_item():
    from app.integrations.azure_devops.tools import create_work_item

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 101}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.azure_devops.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await create_work_item("user-1", "myorg", "myproject", "Task", "New task", "Do something")
        assert "101" in result


async def test_trigger_pipeline():
    from app.integrations.azure_devops.tools import trigger_pipeline

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 55, "state": "inProgress"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.azure_devops.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await trigger_pipeline("user-1", "myorg", "myproject", "10")
        assert "55" in result
        assert "inProgress" in result


async def test_azure_devops_is_connected():
    from app.integrations.azure_devops import AzureDevOpsIntegration

    integration = AzureDevOpsIntegration()
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value='{"access_token": "az-tok"}')
        assert await integration.is_connected("user-1") is True
