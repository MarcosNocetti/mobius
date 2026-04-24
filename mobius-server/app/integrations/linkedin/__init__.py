import json

import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.base import IntegrationBase


class LinkedInIntegration(IntegrationBase):
    name = "linkedin"
    display_name = "LinkedIn"
    auth_type = "oauth2"
    scopes = ["r_liteprofile", "w_member_social"]
    base_api_url = "https://api.linkedin.com/v2"
    auth_url = "https://www.linkedin.com/oauth/v2/authorization"
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"

    def _get_client_id(self) -> str:
        return settings.LINKEDIN_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.LINKEDIN_CLIENT_SECRET


# ---- Legacy FastAPI router (kept for backward compat until Task 6) ----

router = APIRouter(prefix="/integrations/linkedin", tags=["linkedin"])

_integration = LinkedInIntegration()


@router.get("/authorize")
async def linkedin_authorize(user_id: str):
    url = _integration.get_authorize_url(user_id, settings.BASE_URL)
    return RedirectResponse(url)


@router.get("/callback")
async def linkedin_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(_integration.token_url, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{settings.BASE_URL}/integrations/linkedin/callback",
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "client_secret": settings.LINKEDIN_CLIENT_SECRET,
        })
        resp.raise_for_status()
        tokens = resp.json()
        access_token = tokens["access_token"]

        me_resp = await client.get(
            "https://api.linkedin.com/v2/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        me_resp.raise_for_status()
        person_id = me_resp.json()["id"]

    await redis_client.set(f"oauth:linkedin:{state}", json.dumps({
        "access_token": access_token,
        "person_urn": f"urn:li:person:{person_id}",
    }))
    return {"status": "connected", "user_id": state}
