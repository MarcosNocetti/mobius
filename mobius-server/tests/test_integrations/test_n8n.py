import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


async def test_list_n8n_workflows():
    from app.integrations.n8n.tools import list_n8n_workflows

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "1", "name": "Workflow A", "active": True},
            {"id": "2", "name": "Workflow B", "active": False},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.n8n.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await list_n8n_workflows("user-1")
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "Workflow A"


async def test_execute_n8n_workflow():
    from app.integrations.n8n.tools import execute_n8n_workflow

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"executionId": "exec-789"}}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.n8n.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await execute_n8n_workflow("user-1", "wf-1")
        assert "exec-789" in result


async def test_n8n_is_connected():
    from app.integrations.n8n import N8nIntegration

    integration = N8nIntegration()
    with patch("app.integrations.n8n.settings") as mock_settings:
        mock_settings.N8N_BASE_URL = "http://localhost:5678"
        assert await integration.is_connected("user-1") is True

        mock_settings.N8N_BASE_URL = ""
        assert await integration.is_connected("user-1") is False
