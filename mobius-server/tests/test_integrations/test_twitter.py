import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_post_tweet(monkeypatch):
    """post_tweet should POST to Twitter API v2."""
    from app.integrations import twitter as tmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "tw-tok"}')
    monkeypatch.setattr(tmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"id": "tweet-789", "text": "Hello!"}}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.twitter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http

        result = await tmod.post_tweet(user_id="user-1", text="Hello!")
    assert result["data"]["id"] == "tweet-789"
