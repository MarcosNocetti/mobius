import json
import base64
import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.redis import redis_client

router = APIRouter(prefix="/integrations/notion", tags=["notion"])

NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"


@router.get("/authorize")
async def notion_authorize(user_id: str):
    params = {
        "client_id": settings.NOTION_CLIENT_ID,
        "redirect_uri": f"{settings.BASE_URL}/integrations/notion/callback",
        "response_type": "code",
        "state": user_id,
    }
    url = NOTION_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback")
async def notion_callback(code: str, state: str):
    creds = base64.b64encode(f"{settings.NOTION_CLIENT_ID}:{settings.NOTION_CLIENT_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            NOTION_TOKEN_URL,
            headers={"Authorization": f"Basic {creds}"},
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{settings.BASE_URL}/integrations/notion/callback",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

    await redis_client.set(f"oauth:notion:{state}", json.dumps({
        "access_token": tokens["access_token"],
        "workspace_id": tokens.get("workspace_id", ""),
    }))
    return {"status": "connected", "user_id": state}


async def create_notion_page(user_id: str, title: str, content: str) -> dict:
    raw = await redis_client.get(f"oauth:notion:{user_id}")
    if not raw:
        raise ValueError(f"No Notion tokens for user {user_id}")
    data = json.loads(raw)
    token = data["access_token"]

    page_body = {
        "parent": {"type": "workspace", "workspace": True},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]}
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
            },
            json=page_body,
        )
        resp.raise_for_status()
        return resp.json()
