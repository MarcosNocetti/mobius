import json
import logging
import base64
from email.mime.text import MIMEText
import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse, HTMLResponse
from app.core.config import settings
from app.core.redis import redis_client

logger = logging.getLogger("mobius.google")

router = APIRouter(prefix="/integrations/google", tags=["google"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/tasks",
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
    html = """<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>body{background:#0a0a1a;color:#e0e0e0;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
    .card{text-align:center;background:#1a1a2e;padding:3rem;border-radius:16px;border:2px solid #4ade80}
    h1{color:#4ade80;font-size:2rem}p{color:#bbb;margin-top:1rem}</style></head>
    <body><div class="card"><h1>✅ Google conectado!</h1><p>Pode fechar esta aba e voltar ao chat.</p></div></body></html>"""
    return HTMLResponse(content=html)


async def _refresh_access_token(user_id: str, tokens: dict) -> str:
    """Use the refresh_token to get a new access_token."""
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise ValueError("No refresh token available — user must re-authorize")

    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        new_tokens = resp.json()

    # Merge — Google doesn't return refresh_token on refresh, keep the old one
    tokens["access_token"] = new_tokens["access_token"]
    if "expires_in" in new_tokens:
        tokens["expires_in"] = new_tokens["expires_in"]
    await redis_client.set(f"oauth:google:{user_id}", json.dumps(tokens))

    logger.info(f"[google] refreshed access token for user {user_id}")
    return new_tokens["access_token"]


async def _get_access_token(user_id: str) -> str:
    """Get a valid access token, refreshing if expired."""
    raw = await redis_client.get(f"oauth:google:{user_id}")
    if not raw:
        raise ValueError(f"No Google tokens for user {user_id}")
    tokens = json.loads(raw)
    return tokens["access_token"], tokens


async def _google_request(method: str, url: str, user_id: str, **kwargs) -> httpx.Response:
    """Make a Google API request with automatic token refresh on 401."""
    access_token, tokens = await _get_access_token(user_id)

    async with httpx.AsyncClient() as client:
        resp = await getattr(client, method)(
            url, headers={"Authorization": f"Bearer {access_token}"}, **kwargs
        )

        # If 401, try refreshing the token and retry once
        if resp.status_code == 401:
            logger.info(f"[google] 401 for user {user_id}, refreshing token...")
            new_token = await _refresh_access_token(user_id, tokens)
            resp = await getattr(client, method)(
                url, headers={"Authorization": f"Bearer {new_token}"}, **kwargs
            )

        resp.raise_for_status()
        return resp


async def create_calendar_event(user_id: str, title: str, start_dt: str, end_dt: str) -> dict:
    event_body = {
        "summary": title,
        "start": {"dateTime": start_dt, "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": end_dt, "timeZone": "America/Sao_Paulo"},
    }
    resp = await _google_request(
        "post", "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        user_id, json=event_body,
    )
    return resp.json()


async def send_gmail(user_id: str, to: str, subject: str, body: str) -> dict:
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    resp = await _google_request(
        "post", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        user_id, json={"raw": raw},
    )
    return resp.json()


async def read_gmail(user_id: str, query: str = "is:unread", max_results: int = 5) -> list[dict]:
    """Search and read Gmail messages."""
    resp = await _google_request(
        "get", "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        user_id, params={"q": query, "maxResults": max_results},
    )
    messages = resp.json().get("messages", [])
    results = []
    for msg in messages[:max_results]:
        detail = await _google_request(
            "get", f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
            user_id, params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
        )
        headers = {h["name"]: h["value"] for h in detail.json().get("payload", {}).get("headers", [])}
        results.append({"id": msg["id"], "from": headers.get("From", ""), "subject": headers.get("Subject", ""), "date": headers.get("Date", "")})
    return results


async def list_calendar_events(user_id: str, time_min: str, time_max: str, max_results: int = 10) -> list[dict]:
    """List calendar events in a time range."""
    resp = await _google_request(
        "get", "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        user_id, params={"timeMin": time_min, "timeMax": time_max, "maxResults": max_results, "singleEvents": "true", "orderBy": "startTime"},
    )
    events = resp.json().get("items", [])
    return [{"id": e["id"], "summary": e.get("summary", ""), "start": e.get("start", {}), "end": e.get("end", {})} for e in events]


async def create_google_doc(user_id: str, title: str, content: str) -> dict:
    """Create a Google Doc with text content."""
    resp = await _google_request(
        "post", "https://docs.googleapis.com/v1/documents",
        user_id, json={"title": title},
    )
    doc = resp.json()
    doc_id = doc["documentId"]
    if content:
        await _google_request(
            "post", f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
            user_id, json={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        )
    return {"documentId": doc_id, "title": title, "url": f"https://docs.google.com/document/d/{doc_id}"}


async def create_spreadsheet(user_id: str, title: str, data: list[list[str]] | None = None) -> dict:
    """Create a Google Spreadsheet with optional initial data."""
    resp = await _google_request(
        "post", "https://sheets.googleapis.com/v4/spreadsheets",
        user_id, json={"properties": {"title": title}},
    )
    sheet = resp.json()
    sheet_id = sheet["spreadsheetId"]
    if data:
        await _google_request(
            "put", f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/A1",
            user_id, params={"valueInputOption": "RAW"}, json={"values": data},
        )
    return {"spreadsheetId": sheet_id, "title": title, "url": f"https://docs.google.com/spreadsheets/d/{sheet_id}"}


async def list_drive_files(user_id: str, query: str = "", max_results: int = 10) -> list[dict]:
    """Search Google Drive files."""
    params = {"pageSize": max_results, "fields": "files(id,name,mimeType,webViewLink,modifiedTime)"}
    if query:
        params["q"] = f"name contains '{query}'"
    resp = await _google_request(
        "get", "https://www.googleapis.com/drive/v3/files",
        user_id, params=params,
    )
    return resp.json().get("files", [])


async def create_task(user_id: str, title: str, notes: str = "", due: str = "") -> dict:
    """Create a Google Task."""
    task_body = {"title": title}
    if notes:
        task_body["notes"] = notes
    if due:
        task_body["due"] = due
    resp = await _google_request(
        "post", "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks",
        user_id, json=task_body,
    )
    return resp.json()


async def list_tasks(user_id: str, max_results: int = 10) -> list[dict]:
    """List Google Tasks."""
    resp = await _google_request(
        "get", "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks",
        user_id, params={"maxResults": max_results},
    )
    return [{"id": t["id"], "title": t.get("title", ""), "status": t.get("status", ""), "due": t.get("due", "")} for t in resp.json().get("items", [])]
