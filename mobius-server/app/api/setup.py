"""
Google OAuth connect endpoint — user clicks "Connect Google" in the app
or gets redirected here when the AI detects Google isn't connected.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.redis import redis_client
from sqlalchemy import select

router = APIRouter(tags=["setup"])


@router.get("/connect/google")
async def connect_google(request: Request, user_id: str | None = None):
    """Start Google OAuth. Called from app Integrations tab or from chat redirect."""
    base_url = settings.BASE_URL or str(request.base_url).rstrip("/")

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return HTMLResponse(
            "<h2>Google OAuth not configured</h2>"
            "<p>Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment.</p>",
            status_code=500,
        )

    # Resolve user_id — use provided or fallback to first registered user
    if not user_id:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if not user:
                return HTMLResponse("No registered users. Sign up first.", status_code=400)
            user_id = str(user.id)

    scopes = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.send"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{base_url}/integrations/google/callback",
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
        "state": user_id,
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=url)


@router.get("/connect/google/status")
async def google_status(user_id: str):
    """Check if a user has Google connected. Used by the app."""
    try:
        raw = await redis_client.get(f"oauth:google:{user_id}")
        return {"connected": bool(raw)}
    except Exception:
        return {"connected": False}
