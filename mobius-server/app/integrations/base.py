import json
import logging
from abc import ABC, abstractmethod
from urllib.parse import urlencode
import httpx
from app.core.redis import redis_client

logger = logging.getLogger("mobius.integration")


class IntegrationBase(ABC):
    name: str = ""
    display_name: str = ""
    auth_type: str = "oauth2"
    scopes: list[str] = []
    base_api_url: str = ""
    auth_url: str = ""
    token_url: str = ""

    @abstractmethod
    def _get_client_id(self) -> str: ...

    @abstractmethod
    def _get_client_secret(self) -> str: ...

    def _redis_key(self, user_id: str) -> str:
        return f"oauth:{self.name}:{user_id}"

    def get_authorize_url(self, user_id: str, base_url: str) -> str:
        params = {
            "client_id": self._get_client_id(),
            "redirect_uri": f"{base_url}/connect/{self.name}/callback",
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": user_id,
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str, base_url: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data={
                "code": code,
                "client_id": self._get_client_id(),
                "client_secret": self._get_client_secret(),
                "redirect_uri": f"{base_url}/connect/{self.name}/callback",
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            tokens = resp.json()
        await redis_client.set(self._redis_key(state), json.dumps(tokens))
        logger.info(f"[{self.name}] tokens stored for user {state}")
        return tokens

    async def is_connected(self, user_id: str) -> bool:
        raw = await redis_client.get(self._redis_key(user_id))
        return bool(raw)

    async def get_access_token(self, user_id: str) -> tuple[str, dict]:
        raw = await redis_client.get(self._redis_key(user_id))
        if not raw:
            raise ValueError(f"No {self.name} tokens for user {user_id}")
        tokens = json.loads(raw if isinstance(raw, str) else raw.decode())
        return tokens["access_token"], tokens

    async def refresh_token(self, user_id: str, tokens: dict) -> str:
        refresh = tokens.get("refresh_token")
        if not refresh:
            raise ValueError(f"No refresh token for {self.name}")
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data={
                "client_id": self._get_client_id(),
                "client_secret": self._get_client_secret(),
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            new_tokens = resp.json()
        tokens["access_token"] = new_tokens["access_token"]
        await redis_client.set(self._redis_key(user_id), json.dumps(tokens))
        return new_tokens["access_token"]

    async def api_request(self, method: str, url: str, user_id: str, **kwargs) -> httpx.Response:
        if not url.startswith("http"):
            url = f"{self.base_api_url}{url}"
        access_token, tokens = await self.get_access_token(user_id)
        async with httpx.AsyncClient() as client:
            resp = await getattr(client, method)(
                url, headers={"Authorization": f"Bearer {access_token}"}, **kwargs
            )
            if resp.status_code == 401:
                logger.info(f"[{self.name}] 401, refreshing token...")
                new_token = await self.refresh_token(user_id, tokens)
                resp = await getattr(client, method)(
                    url, headers={"Authorization": f"Bearer {new_token}"}, **kwargs
                )
            resp.raise_for_status()
            return resp

    async def to_status_dict(self, user_id: str) -> dict:
        connected = await self.is_connected(user_id)
        return {
            "name": self.name,
            "display_name": self.display_name,
            "connected": connected,
            "auth_type": self.auth_type,
        }
