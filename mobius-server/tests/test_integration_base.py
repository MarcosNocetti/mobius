import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.integrations.base import IntegrationBase


class FakeIntegration(IntegrationBase):
    name = "fake"
    display_name = "Fake Service"
    auth_type = "oauth2"
    scopes = ["read", "write"]
    base_api_url = "https://api.fake.com"
    auth_url = "https://fake.com/oauth/authorize"
    token_url = "https://fake.com/oauth/token"

    def _get_client_id(self):
        return "fake-client-id"

    def _get_client_secret(self):
        return "fake-client-secret"


@pytest.fixture
def integration():
    return FakeIntegration()


def test_get_authorize_url(integration):
    url = integration.get_authorize_url("user-1", "https://myapp.com")
    assert "fake-client-id" in url
    assert "user-1" in url
    assert "myapp.com" in url


async def test_is_connected_false_when_no_token(integration):
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        result = await integration.is_connected("user-1")
        assert result is False


async def test_is_connected_true_when_token_exists(integration):
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value=json.dumps({"access_token": "tok"}).encode())
        result = await integration.is_connected("user-1")
        assert result is True


async def test_handle_callback_stores_tokens(integration):
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "new-tok", "refresh_token": "ref-tok"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.base.redis_client") as mock_redis, \
         patch("app.integrations.base.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_redis.set = AsyncMock()

        tokens = await integration.handle_callback("auth-code", "user-1", "https://myapp.com")
        assert tokens["access_token"] == "new-tok"
        mock_redis.set.assert_called_once()


async def test_to_status_dict(integration):
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        status = await integration.to_status_dict("user-1")
        assert status["name"] == "fake"
        assert status["display_name"] == "Fake Service"
        assert status["connected"] is False
        assert status["auth_type"] == "oauth2"
