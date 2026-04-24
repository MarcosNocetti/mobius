import json

import httpx

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.base import IntegrationBase


class GitHubIntegration(IntegrationBase):
    name = "github"
    display_name = "GitHub"
    auth_type = "oauth2"
    scopes = ["repo", "read:user", "read:org"]
    base_api_url = "https://api.github.com"
    auth_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"

    def _get_client_id(self) -> str:
        return settings.GITHUB_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.GITHUB_CLIENT_SECRET

    async def handle_callback(self, code: str, state: str, base_url: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.token_url,
                data={
                    "client_id": self._get_client_id(),
                    "client_secret": self._get_client_secret(),
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            tokens = resp.json()
        await redis_client.set(self._redis_key(state), json.dumps(tokens))
        return tokens
