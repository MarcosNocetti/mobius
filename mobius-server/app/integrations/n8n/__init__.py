import httpx

from app.core.config import settings
from app.integrations.base import IntegrationBase


class N8nIntegration(IntegrationBase):
    name = "n8n"
    display_name = "n8n"
    auth_type = "api_key"
    scopes = []

    def _get_client_id(self) -> str:
        return ""

    def _get_client_secret(self) -> str:
        return ""

    async def is_connected(self, user_id: str) -> bool:
        return bool(settings.N8N_BASE_URL)

    async def api_request(self, method: str, url: str, user_id: str, **kwargs) -> httpx.Response:
        if not url.startswith("http"):
            url = f"{settings.N8N_BASE_URL}/api/v1{url}"
        headers = kwargs.pop("headers", {})
        headers["X-N8N-API-KEY"] = settings.N8N_BASE_URL
        async with httpx.AsyncClient() as client:
            resp = await getattr(client, method)(url, headers=headers, **kwargs)
            resp.raise_for_status()
            return resp
