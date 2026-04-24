import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_post_tweet(monkeypatch):
    """post_tweet should POST to Twitter API v2."""
    from app.integrations.twitter import tools as ttools

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"id": "tweet-789", "text": "Hello!"}}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.twitter.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration

        result = await ttools.post_tweet(user_id="user-1", text="Hello!")
    assert "tweet-789" in result
