import json

from fastapi import APIRouter
from fastapi.responses import RedirectResponse, HTMLResponse

from app.core.config import settings
from app.core.redis import redis_client
from app.integrations.base import IntegrationBase
from urllib.parse import urlencode


class GoogleIntegration(IntegrationBase):
    name = "google"
    display_name = "Google"
    auth_type = "oauth2"
    scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/tasks",
    ]
    base_api_url = "https://www.googleapis.com"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"

    def _get_client_id(self) -> str:
        return settings.GOOGLE_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.GOOGLE_CLIENT_SECRET

    def get_authorize_url(self, user_id: str, base_url: str) -> str:
        params = {
            "client_id": self._get_client_id(),
            "redirect_uri": f"{base_url}/integrations/google/callback",
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": user_id,
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str, base_url: str) -> dict:
        """Override to use legacy redirect URI that matches Google Cloud Console."""
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data={
                "code": code,
                "client_id": self._get_client_id(),
                "client_secret": self._get_client_secret(),
                "redirect_uri": f"{base_url}/integrations/google/callback",
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            tokens = resp.json()
        await redis_client.set(self._redis_key(state), json.dumps(tokens))
        return tokens


# ---- Legacy FastAPI router (kept for backward compat until Task 6) ----

router = APIRouter(prefix="/integrations/google", tags=["google"])

_integration = GoogleIntegration()


@router.get("/authorize")
async def google_authorize(user_id: str):
    url = _integration.get_authorize_url(user_id, settings.BASE_URL)
    return RedirectResponse(url)


@router.get("/callback")
async def google_callback(code: str, state: str):
    await _integration.handle_callback(code, state, settings.BASE_URL)
    html = """<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>body{background:#0a0a1a;color:#e0e0e0;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
    .card{text-align:center;background:#1a1a2e;padding:3rem;border-radius:16px;border:2px solid #4ade80}
    h1{color:#4ade80;font-size:2rem}p{color:#bbb;margin-top:1rem}</style></head>
    <body><div class="card"><h1>Google conectado!</h1><p>Pode fechar esta aba e voltar ao chat.</p></div></body></html>"""
    return HTMLResponse(content=html)
