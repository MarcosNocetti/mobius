import json
import base64

import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.base import IntegrationBase


class NotionIntegration(IntegrationBase):
    name = "notion"
    display_name = "Notion"
    auth_type = "oauth2"
    scopes = []
    base_api_url = "https://api.notion.com/v1"
    auth_url = "https://api.notion.com/v1/oauth/authorize"
    token_url = "https://api.notion.com/v1/oauth/token"

    def _get_client_id(self) -> str:
        return settings.NOTION_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.NOTION_CLIENT_SECRET

    async def api_request(self, method: str, url: str, user_id: str, **kwargs) -> httpx.Response:
        # Inject Notion-Version header
        headers = kwargs.pop("headers", {})
        headers["Notion-Version"] = "2022-06-28"
        kwargs["headers"] = headers
        return await super().api_request(method, url, user_id, **kwargs)


# ---- Legacy FastAPI router (kept for backward compat until Task 6) ----

router = APIRouter(prefix="/integrations/notion", tags=["notion"])

_integration = NotionIntegration()


@router.get("/authorize")
async def notion_authorize(user_id: str):
    url = _integration.get_authorize_url(user_id, settings.BASE_URL)
    return RedirectResponse(url)


@router.get("/callback")
async def notion_callback(code: str, state: str):
    await _integration.handle_callback(code, state, settings.BASE_URL)
    return {"status": "connected", "user_id": state}
