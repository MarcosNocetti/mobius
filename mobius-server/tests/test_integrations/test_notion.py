import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_create_notion_page(monkeypatch):
    """create_notion_page should POST to Notion API."""
    from app.integrations.notion import tools as ntools

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "page-abc", "url": "https://notion.so/page-abc"}
    mock_response.raise_for_status = MagicMock()

    mock_integration = MagicMock()
    mock_integration.api_request = AsyncMock(return_value=mock_response)

    with patch("app.integrations.notion.tools.integration_registry") as mock_registry:
        mock_registry.get.return_value = mock_integration

        result = await ntools.create_notion_page(
            user_id="user-1",
            title="My Page",
            content="Hello from Mobius"
        )
    assert "page-abc" in result or "notion.so" in result


async def test_post_linkedin(monkeypatch):
    """post_linkedin should POST to LinkedIn UGC Share API."""
    from app.integrations.linkedin import tools as ltools

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "li-tok", "person_urn": "urn:li:person:abc"}')
    monkeypatch.setattr(ltools, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "share-xyz"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_http

        result = await ltools.post_linkedin(user_id="user-1", text="Hello LinkedIn!")
    assert "share-xyz" in result
