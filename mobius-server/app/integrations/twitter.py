import json
import hashlib
import secrets
import base64
import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.redis import redis_client

router = APIRouter(prefix="/integrations/twitter", tags=["twitter"])

TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
SCOPES = "tweet.read tweet.write users.read offline.access"


def _generate_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(43)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


@router.get("/authorize")
async def twitter_authorize(user_id: str):
    verifier, challenge = _generate_pkce()
    await redis_client.set(f"pkce:twitter:{user_id}", verifier, ex=600)
    params = {
        "response_type": "code",
        "client_id": settings.TWITTER_CLIENT_ID,
        "redirect_uri": f"{settings.BASE_URL}/integrations/twitter/callback",
        "scope": SCOPES,
        "state": user_id,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = TWITTER_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback")
async def twitter_callback(code: str, state: str):
    verifier = await redis_client.get(f"pkce:twitter:{state}")
    if not verifier:
        return {"error": "PKCE verifier not found"}
    verifier = verifier.decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TWITTER_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{settings.BASE_URL}/integrations/twitter/callback",
                "code_verifier": verifier,
                "client_id": settings.TWITTER_CLIENT_ID,
            },
            auth=(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET),
        )
        resp.raise_for_status()
        tokens = resp.json()

    await redis_client.set(f"oauth:twitter:{state}", json.dumps(tokens))
    return {"status": "connected", "user_id": state}


async def post_tweet(user_id: str, text: str) -> dict:
    raw = await redis_client.get(f"oauth:twitter:{user_id}")
    if not raw:
        raise ValueError(f"No Twitter tokens for user {user_id}")
    token = json.loads(raw)["access_token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.twitter.com/2/tweets",
            headers={"Authorization": f"Bearer {token}"},
            json={"text": text},
        )
        resp.raise_for_status()
        return resp.json()
