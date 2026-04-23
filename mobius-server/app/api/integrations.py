from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.core.security import decode_token
from app.core.redis import redis_client
from app.integrations.google import router as google_router
from app.integrations.twitter import router as twitter_router
from app.integrations.instagram import router as instagram_router
from app.integrations.notion import router as notion_router
from app.integrations.linkedin import router as linkedin_router

router = APIRouter()
router.include_router(google_router)
router.include_router(twitter_router)
router.include_router(instagram_router)
router.include_router(notion_router)
router.include_router(linkedin_router)

bearer = HTTPBearer(auto_error=False)


@router.get("/integrations/status")
async def integrations_status(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    """Return connection status for each integration."""
    user_id = None
    if creds:
        try:
            user_id = decode_token(creds.credentials)
        except JWTError:
            pass

    statuses = {"google": False, "twitter": False, "instagram": False, "linkedin": False, "notion": False}
    if user_id:
        for provider in statuses:
            try:
                raw = await redis_client.get(f"oauth:{provider}:{user_id}")
                statuses[provider] = bool(raw)
            except Exception:
                pass

    return statuses
