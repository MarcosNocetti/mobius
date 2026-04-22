import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_create_notion_page(monkeypatch):
    """create_notion_page should POST to Notion API."""
    from app.integrations import notion as nmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "notion-tok", "workspace_id": "ws-1"}')
    monkeypatch.setattr(nmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "page-abc", "url": "https://notion.so/page-abc"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.notion.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_http

        result = await nmod.create_notion_page(
            user_id="user-1",
            title="My Page",
            content="Hello from Mobius"
        )
    assert result["id"] == "page-abc"


async def test_post_linkedin(monkeypatch):
    """post_linkedin should POST to LinkedIn UGC Share API."""
    from app.integrations import linkedin as lmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "li-tok", "person_urn": "urn:li:person:abc"}')
    monkeypatch.setattr(lmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "share-xyz"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.linkedin.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_http

        result = await lmod.post_linkedin(user_id="user-1", text="Hello LinkedIn!")
    assert result["id"] == "share-xyz"
