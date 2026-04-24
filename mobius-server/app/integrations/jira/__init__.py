import json

import httpx

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.base import IntegrationBase
from urllib.parse import urlencode


class JiraIntegration(IntegrationBase):
    name = "jira"
    display_name = "Jira"
    auth_type = "oauth2"
    scopes = ["read:jira-work", "write:jira-work", "read:jira-user", "offline_access"]
    base_api_url = ""  # constructed per-request via cloud_id
    auth_url = "https://auth.atlassian.com/authorize"
    token_url = "https://auth.atlassian.com/oauth/token"

    def _get_client_id(self) -> str:
        return settings.JIRA_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.JIRA_CLIENT_SECRET

    def get_authorize_url(self, user_id: str, base_url: str) -> str:
        params = {
            "client_id": self._get_client_id(),
            "redirect_uri": f"{base_url}/connect/{self.name}/callback",
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": user_id,
            "audience": "api.atlassian.com",
            "prompt": "consent",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str, base_url: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.token_url,
                json={
                    "grant_type": "authorization_code",
                    "client_id": self._get_client_id(),
                    "client_secret": self._get_client_secret(),
                    "code": code,
                    "redirect_uri": f"{base_url}/connect/{self.name}/callback",
                },
            )
            resp.raise_for_status()
            tokens = resp.json()

        # Fetch cloud_id from accessible resources
        resources_resp = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        resources = resources_resp.json()
        if resources:
            tokens["cloud_id"] = resources[0]["id"]

        await redis_client.set(self._redis_key(state), json.dumps(tokens))
        return tokens

    async def get_cloud_id(self, user_id: str) -> str:
        raw = await redis_client.get(self._redis_key(user_id))
        if not raw:
            raise ValueError(f"No Jira tokens for user {user_id}")
        tokens = json.loads(raw if isinstance(raw, str) else raw.decode())
        cloud_id = tokens.get("cloud_id")
        if not cloud_id:
            raise ValueError("No Jira cloud_id found. Please reconnect.")
        return cloud_id

    async def api_request(self, method: str, url: str, user_id: str, **kwargs) -> httpx.Response:
        if not url.startswith("http"):
            cloud_id = await self.get_cloud_id(user_id)
            url = f"https://api.atlassian.com/ex/jira/{cloud_id}{url}"
        return await super().api_request(method, url, user_id, **kwargs)
