import json
import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.redis import redis_client

router = APIRouter(prefix="/integrations/linkedin", tags=["linkedin"])

LI_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LI_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "r_liteprofile w_member_social"


@router.get("/authorize")
async def linkedin_authorize(user_id: str):
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": f"{settings.BASE_URL}/integrations/linkedin/callback",
        "scope": SCOPES,
        "state": user_id,
    }
    url = LI_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback")
async def linkedin_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(LI_TOKEN_URL, data={
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


async def post_linkedin(user_id: str, text: str) -> dict:
    raw = await redis_client.get(f"oauth:linkedin:{user_id}")
    if not raw:
        raise ValueError(f"No LinkedIn tokens for user {user_id}")
    data = json.loads(raw)
    token = data["access_token"]
    person_urn = data["person_urn"]

    share_body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=share_body,
        )
        resp.raise_for_status()
        return resp.json()
