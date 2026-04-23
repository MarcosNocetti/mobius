from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from jose import JWTError
from app.core.database import get_session
from app.core.security import hash_password, verify_password, create_token, encrypt_api_key, decrypt_api_key, decode_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = await session.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, hashed_password=hash_password(body.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse(id=user.id, email=user.email)


@router.post("/token", response_model=TokenResponse)
async def token(body: TokenRequest, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(user.id))


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        user_id = decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class ApiKeyRequest(BaseModel):
    provider: str
    key: str


@router.put("/api-keys")
async def store_api_key(
    body: ApiKeyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    keys = user.api_keys or {}
    keys[body.provider] = encrypt_api_key(body.key)
    user.api_keys = keys
    session.add(user)
    await session.commit()
    return {"status": "stored"}


@router.get("/api-keys")
async def list_api_keys(user: User = Depends(get_current_user)):
    return {"providers": list((user.api_keys or {}).keys())}


class TestKeyRequest(BaseModel):
    provider: str
    key: str


@router.post("/api-keys/test")
async def test_api_key(body: TestKeyRequest):
    """Test an API key by sending a minimal prompt. Returns success or error."""
    import litellm

    model_map = {
        "gemini": "gemini/gemini-2.0-flash",
        "openai": "openai/gpt-4o",
        "anthropic": "anthropic/claude-sonnet-4-6",
    }
    model = model_map.get(body.provider)
    if not model:
        return {"success": False, "error": f"Unknown provider: {body.provider}"}

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": "Say OK"}],
            api_key=body.key,
            max_tokens=5,
        )
        reply = response.choices[0].message.content.strip()
        return {"success": True, "reply": reply}
    except Exception as e:
        return {"success": False, "error": str(e)}
