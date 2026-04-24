import json

import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.base import IntegrationBase


class InstagramIntegration(IntegrationBase):
    name = "instagram"
    display_name = "Instagram"
    auth_type = "oauth2"
    scopes = ["instagram_basic", "instagram_content_publish", "pages_show_list"]
    base_api_url = "https://graph.facebook.com/v19.0"
    auth_url = "https://www.facebook.com/v19.0/dialog/oauth"
    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"

    def _get_client_id(self) -> str:
        return settings.INSTAGRAM_APP_ID

    def _get_client_secret(self) -> str:
        return settings.INSTAGRAM_APP_SECRET


# ---- Legacy FastAPI router (kept for backward compat until Task 6) ----

router = APIRouter(prefix="/integrations/instagram", tags=["instagram"])

_integration = InstagramIntegration()

GRAPH_URL = "https://graph.facebook.com/v19.0"


@router.get("/authorize")
async def instagram_authorize(user_id: str):
    url = _integration.get_authorize_url(user_id, settings.BASE_URL)
    return RedirectResponse(url)


@router.get("/callback")
async def instagram_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(_integration.token_url, params={
            "client_id": settings.INSTAGRAM_APP_ID,
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "redirect_uri": f"{settings.BASE_URL}/integrations/instagram/callback",
            "code": code,
        })
        resp.raise_for_status()
        tokens = resp.json()
        access_token = tokens["access_token"]

        pages_resp = await client.get(f"{GRAPH_URL}/me/accounts", params={"access_token": access_token})
        pages_resp.raise_for_status()
        pages = pages_resp.json().get("data", [])
        ig_user_id = pages[0]["id"] if pages else None

    payload = {"access_token": access_token, "ig_user_id": ig_user_id}
    await redis_client.set(f"oauth:instagram:{state}", json.dumps(payload))
    return {"status": "connected", "user_id": state}
