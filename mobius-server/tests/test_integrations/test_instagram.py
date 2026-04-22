import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_post_instagram_photo(monkeypatch):
    """post_photo should call Graph API to create a container then publish it."""
    from app.integrations import instagram as igmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "ig-tok", "ig_user_id": "123456"}')
    monkeypatch.setattr(igmod, "redis_client", mock_redis)

    container_response = MagicMock()
    container_response.json.return_value = {"id": "container-abc"}
    container_response.raise_for_status = MagicMock()

    publish_response = MagicMock()
    publish_response.json.return_value = {"id": "media-xyz"}
    publish_response.raise_for_status = MagicMock()

    with patch("app.integrations.instagram.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(side_effect=[container_response, publish_response])
        mock_cls.return_value = mock_http

        result = await igmod.post_photo(
            user_id="user-1",
            image_url="https://example.com/photo.jpg",
            caption="My cool post"
        )
    assert result["id"] == "media-xyz"
