import hashlib
import secrets
import base64
import json

import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.base import IntegrationBase
from urllib.parse import urlencode


class TwitterIntegration(IntegrationBase):
    name = "twitter"
    display_name = "Twitter / X"
    auth_type = "oauth2_pkce"
    scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]
    base_api_url = "https://api.twitter.com/2"
    auth_url = "https://twitter.com/i/oauth2/authorize"
    token_url = "https://api.twitter.com/2/oauth2/token"

    def _get_client_id(self) -> str:
        return settings.TWITTER_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.TWITTER_CLIENT_SECRET

    @staticmethod
    def _generate_pkce() -> tuple[str, str]:
        verifier = secrets.token_urlsafe(43)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        return verifier, challenge

    def get_authorize_url(self, user_id: str, base_url: str) -> str:
        verifier, challenge = self._generate_pkce()
        # Store verifier synchronously is not possible; we'll need the caller
        # to await _store_pkce separately, or we make this async-aware.
        # For compatibility with IntegrationBase, we store via a sync-compatible
        # side channel.  The registry caller should await store_pkce_verifier after.
        self._pending_pkce = (user_id, verifier)

        params = {
            "response_type": "code",
            "client_id": self._get_client_id(),
            "redirect_uri": f"{base_url}/connect/{self.name}/callback",
            "scope": " ".join(self.scopes),
            "state": user_id,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def store_pkce_verifier(self):
        """Must be called after get_authorize_url to persist the PKCE verifier."""
        if hasattr(self, "_pending_pkce"):
            user_id, verifier = self._pending_pkce
            await redis_client.set(f"pkce:twitter:{user_id}", verifier, ex=600)
            del self._pending_pkce

    async def handle_callback(self, code: str, state: str, base_url: str) -> dict:
        verifier_raw = await redis_client.get(f"pkce:twitter:{state}")
        if not verifier_raw:
            raise ValueError("PKCE verifier not found or expired")
        verifier = verifier_raw if isinstance(verifier_raw, str) else verifier_raw.decode()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{base_url}/connect/{self.name}/callback",
                    "code_verifier": verifier,
                    "client_id": self._get_client_id(),
                },
                auth=(self._get_client_id(), self._get_client_secret()),
            )
            resp.raise_for_status()
            tokens = resp.json()

        await redis_client.set(self._redis_key(state), json.dumps(tokens))
        return tokens


# ---- Legacy FastAPI router (kept for backward compat until Task 6) ----

router = APIRouter(prefix="/integrations/twitter", tags=["twitter"])

_integration = TwitterIntegration()


@router.get("/authorize")
async def twitter_authorize(user_id: str):
    url = _integration.get_authorize_url(user_id, settings.BASE_URL)
    await _integration.store_pkce_verifier()
    return RedirectResponse(url)


@router.get("/callback")
async def twitter_callback(code: str, state: str):
    await _integration.handle_callback(code, state, settings.BASE_URL)
    return {"status": "connected", "user_id": state}
