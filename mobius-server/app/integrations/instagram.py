import json
import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.redis import redis_client

router = APIRouter(prefix="/integrations/instagram", tags=["instagram"])

FB_AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
GRAPH_URL = "https://graph.facebook.com/v19.0"

SCOPES = "instagram_basic,instagram_content_publish,pages_show_list"


@router.get("/authorize")
async def instagram_authorize(user_id: str):
    params = {
        "client_id": settings.INSTAGRAM_APP_ID,
        "redirect_uri": f"{settings.BASE_URL}/integrations/instagram/callback",
        "scope": SCOPES,
        "response_type": "code",
        "state": user_id,
    }
    url = FB_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback")
async def instagram_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(FB_TOKEN_URL, params={
            "client_id": settings.INSTAGRAM_APP_ID,
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "redirect_uri": f"{settings.BASE_URL}/integrations/instagram/callback",
            "code": code,
        })
        resp.raise_for_status()
        tokens = resp.json()
        access_token = tokens["access_token"]

        # Get IG business account ID
        pages_resp = await client.get(f"{GRAPH_URL}/me/accounts", params={"access_token": access_token})
        pages_resp.raise_for_status()
        pages = pages_resp.json().get("data", [])
        ig_user_id = pages[0]["id"] if pages else None

    payload = {"access_token": access_token, "ig_user_id": ig_user_id}
    await redis_client.set(f"oauth:instagram:{state}", json.dumps(payload))
    return {"status": "connected", "user_id": state}


async def post_photo(user_id: str, image_url: str, caption: str) -> dict:
    raw = await redis_client.get(f"oauth:instagram:{user_id}")
    if not raw:
        raise ValueError(f"No Instagram tokens for user {user_id}")
    data = json.loads(raw)
    token = data["access_token"]
    ig_id = data["ig_user_id"]

    async with httpx.AsyncClient() as client:
        # Step 1: create media container
        container = await client.post(f"{GRAPH_URL}/{ig_id}/media", params={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        })
        container.raise_for_status()
        container_id = container.json()["id"]

        # Step 2: publish
        publish = await client.post(f"{GRAPH_URL}/{ig_id}/media_publish", params={
            "creation_id": container_id,
            "access_token": token,
        })
        publish.raise_for_status()
        return publish.json()
