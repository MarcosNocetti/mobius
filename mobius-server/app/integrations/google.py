import json
import base64
from email.mime.text import MIMEText
import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.redis import redis_client

router = APIRouter(prefix="/integrations/google", tags=["google"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
]


@router.get("/authorize")
async def google_authorize(user_id: str):
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.BASE_URL}/integrations/google/callback",
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "state": user_id,
    }
    url = GOOGLE_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


async def exchange_code_for_tokens(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": f"{settings.BASE_URL}/integrations/google/callback",
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        return resp.json()


@router.get("/callback")
async def google_callback(code: str, state: str):
    tokens = await exchange_code_for_tokens(code)
    await redis_client.set(f"oauth:google:{state}", json.dumps(tokens))
    return {"status": "connected", "user_id": state}


async def _get_access_token(user_id: str) -> str:
    raw = await redis_client.get(f"oauth:google:{user_id}")
    if not raw:
        raise ValueError(f"No Google tokens for user {user_id}")
    return json.loads(raw)["access_token"]


async def create_calendar_event(user_id: str, title: str, start_dt: str, end_dt: str) -> dict:
    token = await _get_access_token(user_id)
    event_body = {
        "summary": title,
        "start": {"dateTime": start_dt, "timeZone": "UTC"},
        "end": {"dateTime": end_dt, "timeZone": "UTC"},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {token}"},
            json=event_body,
        )
        resp.raise_for_status()
        return resp.json()


async def send_gmail(user_id: str, to: str, subject: str, body: str) -> dict:
    token = await _get_access_token(user_id)
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {token}"},
            json={"raw": raw},
        )
        resp.raise_for_status()
        return resp.json()
