import httpx

from app.core.config import settings
from app.integrations.base import IntegrationBase


class ClaudePlatformIntegration(IntegrationBase):
    name = "claude_platform"
    display_name = "Claude Platform"
    auth_type = "api_key"
    scopes = []
    base_api_url = "https://api.anthropic.com/v1"

    def _get_client_id(self) -> str:
        return ""

    def _get_client_secret(self) -> str:
        return ""

    async def is_connected(self, user_id: str) -> bool:
        return bool(settings.CLAUDE_API_KEY)

    async def api_request(self, method: str, url: str, user_id: str, **kwargs) -> httpx.Response:
        if not url.startswith("http"):
            url = f"{self.base_api_url}{url}"
        headers = kwargs.pop("headers", {})
        headers["x-api-key"] = settings.CLAUDE_API_KEY
        headers["anthropic-version"] = "2023-06-01"
        async with httpx.AsyncClient() as client:
            resp = await getattr(client, method)(url, headers=headers, **kwargs)
            resp.raise_for_status()
            return resp
