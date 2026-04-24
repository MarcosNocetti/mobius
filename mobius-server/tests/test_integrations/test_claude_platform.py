import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


async def test_create_claude_batch():
    from app.integrations.claude_platform.tools import create_claude_batch

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "batch-abc123"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.claude_platform.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await create_claude_batch("user-1", ["Hello", "World"])
        assert "batch-abc123" in result
        assert "2 requests" in result


async def test_get_claude_batch_status():
    from app.integrations.claude_platform.tools import get_claude_batch_status

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "batch-abc123",
        "processing_status": "ended",
        "request_counts": {"succeeded": 2, "errored": 0},
    }
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.claude_platform.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration
        result = await get_claude_batch_status("user-1", "batch-abc123")
        assert "ended" in result
        assert "batch-abc123" in result


async def test_claude_platform_is_connected():
    from app.integrations.claude_platform import ClaudePlatformIntegration

    integration = ClaudePlatformIntegration()
    with patch("app.integrations.claude_platform.settings") as mock_settings:
        mock_settings.CLAUDE_API_KEY = "sk-ant-test"
        assert await integration.is_connected("user-1") is True

        mock_settings.CLAUDE_API_KEY = ""
        assert await integration.is_connected("user-1") is False
