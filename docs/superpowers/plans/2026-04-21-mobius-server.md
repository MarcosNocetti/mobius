# Mobius Server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Mobius backend — a FastAPI server that orchestrates AI agents, manages integrations, and communicates with the mobile app via REST and WebSocket.

**Architecture:** Thin agent engine using LangGraph for multi-step task orchestration. LiteLLM abstracts multiple AI providers. Each external integration is an isolated module. WebSocket streams AI responses and task progress to the Flutter app in real time.

**Tech Stack:** Python 3.12, FastAPI, PostgreSQL, Redis, LangGraph, LiteLLM, Docker Compose, pytest

---

## Directory Structure

```
mobius-server/
├── app/
│   ├── main.py                   # FastAPI app factory
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── database.py           # SQLAlchemy async engine
│   │   ├── redis.py              # Redis client
│   │   └── security.py          # JWT encode/decode
│   ├── api/
│   │   ├── router.py             # Include all routers
│   │   ├── auth.py               # POST /auth/token
│   │   ├── chat.py               # WS /ws/chat
│   │   ├── integrations.py       # OAuth routes per service
│   │   └── automations.py        # CRUD scheduled automations
│   ├── agents/
│   │   ├── engine.py             # LangGraph agent loop
│   │   └── tools/
│   │       ├── social.py         # post_instagram, post_twitter, post_linkedin
│   │       ├── productivity.py   # create_calendar_event, send_gmail, create_notion_page
│   │       ├── device.py         # open_app, take_screenshot, read_screen (mobile-triggered)
│   │       └── utils.py          # web_search, summarize, generate_image_caption
│   ├── integrations/
│   │   ├── google.py             # Calendar + Gmail OAuth + API calls
│   │   ├── notion.py             # Notion OAuth + API calls
│   │   ├── twitter.py            # Twitter/X OAuth + API calls
│   │   ├── instagram.py          # Instagram Graph API OAuth + calls
│   │   └── linkedin.py           # LinkedIn OAuth + API calls
│   └── models/
│       ├── user.py               # User ORM model
│       ├── conversation.py       # Conversation + Message ORM
│       └── automation.py         # ScheduledAutomation ORM
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_agent_engine.py
│   ├── test_integrations/
│   │   ├── test_google.py
│   │   ├── test_twitter.py
│   │   └── test_notion.py
│   └── test_automations.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## Task 1: Project Scaffold

**Goal:** Create the project skeleton — Docker Compose environment, Dockerfile, dependencies, config, and a running health check endpoint.

### Step 1.1 — Write the failing test first

- [ ] Create `tests/conftest.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

- [ ] Create `tests/test_health.py`:

```python
import pytest

async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] Run test (should fail — `app.main` does not exist yet):

```bash
cd mobius-server && pytest tests/test_health.py -v
# Expected: ImportError or ModuleNotFoundError
```

### Step 1.2 — Create `pyproject.toml`

- [ ] Create `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Step 1.3 — Create `requirements.txt`

- [ ] Create `requirements.txt`:

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
redis==5.2.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic-settings==2.6.1
langchain==0.3.9
langgraph==0.2.53
litellm==1.52.14
httpx==0.27.2
apscheduler==3.10.4
cryptography==43.0.3
pytest==8.3.3
pytest-asyncio==0.24.0
```

### Step 1.4 — Create `app/core/config.py`

- [ ] Create `app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://mobius:mobius@localhost:5432/mobius"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production-32-bytes!!"
    GEMINI_API_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days


settings = Settings()
```

### Step 1.5 — Create `app/main.py`

- [ ] Create `app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Mobius Server", version="0.1.0")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

### Step 1.6 — Create `Dockerfile`

- [ ] Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 1.7 — Create `docker-compose.yml`

- [ ] Create `docker-compose.yml`:

```yaml
version: "3.9"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://mobius:mobius@postgres:5432/mobius
      REDIS_URL: redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: mobius
      POSTGRES_PASSWORD: mobius
      POSTGRES_DB: mobius
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mobius"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
```

### Step 1.8 — Create `.env.example`

- [ ] Create `.env.example`:

```
DATABASE_URL=postgresql+asyncpg://mobius:mobius@localhost:5432/mobius
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-in-production-32-bytes!!
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
TWITTER_CLIENT_ID=
TWITTER_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
INSTAGRAM_APP_ID=
INSTAGRAM_APP_SECRET=
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
NOTION_CLIENT_ID=
NOTION_CLIENT_SECRET=
FERNET_KEY=
```

### Step 1.9 — Run test (should pass now)

- [ ] Install dependencies and run:

```bash
pip install -r requirements.txt
pytest tests/test_health.py -v
# Expected:
# PASSED tests/test_health.py::test_health_check
```

### Step 1.10 — Commit

```bash
git add .
git commit -m "chore: scaffold mobius-server project with health check endpoint"
```

---

## Task 2: Auth (JWT)

**Goal:** Implement user registration, login, and JWT-based authentication with an async PostgreSQL-backed user store.

### Step 2.1 — Write failing tests first

- [ ] Create `tests/test_auth.py`:

```python
import pytest

async def test_register_creates_user(client):
    response = await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data

async def test_token_returns_jwt(client):
    await client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "pass1234"
    })
    response = await client.post("/auth/token", json={
        "email": "user@example.com",
        "password": "pass1234"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_invalid_credentials_returns_401(client):
    response = await client.post("/auth/token", json={
        "email": "nobody@example.com",
        "password": "wrong"
    })
    assert response.status_code == 401
```

- [ ] Run test (should fail):

```bash
pytest tests/test_auth.py -v
# Expected: 404 Not Found on /auth/register and /auth/token
```

### Step 2.2 — Create `app/models/user.py`

- [ ] Create `app/models/user.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    api_keys: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Step 2.3 — Create `app/core/database.py`

- [ ] Create `app/core/database.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models.user import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

### Step 2.4 — Create `app/core/security.py`

- [ ] Create `app/core/security.py`:

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> str:
    """Returns user_id (sub) or raises JWTError."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    return payload["sub"]


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32].ljust(32, b"="))
    return Fernet(key)


def encrypt_api_key(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()
```

### Step 2.5 — Create `app/api/auth.py`

- [ ] Create `app/api/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.core.database import get_session
from app.core.security import hash_password, verify_password, create_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


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
```

### Step 2.6 — Create `app/api/router.py`

- [ ] Create `app/api/router.py`:

```python
from fastapi import APIRouter
from app.api import auth

router = APIRouter()
router.include_router(auth.router)
```

### Step 2.7 — Update `app/main.py` to wire DB and router

- [ ] Update `app/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Mobius Server", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

### Step 2.8 — Update `tests/conftest.py` to use in-memory SQLite for tests

- [ ] Update `tests/conftest.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.user import Base
from app.core.database import get_session
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
async def setup_test_db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

- [ ] Add `aiosqlite` to `requirements.txt`:

```
aiosqlite==0.20.0
```

### Step 2.9 — Run tests (should pass)

```bash
pytest tests/test_auth.py tests/test_health.py -v
# Expected:
# PASSED tests/test_health.py::test_health_check
# PASSED tests/test_auth.py::test_register_creates_user
# PASSED tests/test_auth.py::test_token_returns_jwt
# PASSED tests/test_auth.py::test_invalid_credentials_returns_401
```

### Step 2.10 — Commit

```bash
git add .
git commit -m "feat: add user registration and JWT authentication"
```

---

## Task 3: WebSocket Chat Endpoint

**Goal:** Implement a WebSocket endpoint that accepts authenticated connections, receives chat messages, and streams back mock responses token by token. Persist conversations to the database.

### Step 3.1 — Write failing tests first

- [ ] Create `tests/test_chat.py`:

```python
import pytest
import json
from httpx import AsyncClient, ASGITransport

async def _register_and_token(client: AsyncClient) -> str:
    await client.post("/auth/register", json={"email": "ws@test.com", "password": "pass"})
    r = await client.post("/auth/token", json={"email": "ws@test.com", "password": "pass"})
    return r.json()["access_token"]


async def test_ws_requires_token(client):
    """Connection without token should be rejected with 403."""
    from starlette.testclient import TestClient
    from app.main import app as fastapi_app
    with TestClient(fastapi_app) as tc:
        with pytest.raises(Exception):
            with tc.websocket_connect("/ws/chat"):
                pass


async def test_ws_streams_tokens(client):
    """Valid token produces streaming token chunks and a done event."""
    token = await _register_and_token(client)
    from starlette.testclient import TestClient
    from app.main import app as fastapi_app
    with TestClient(fastapi_app) as tc:
        with tc.websocket_connect(f"/ws/chat?token={token}") as ws:
            ws.send_text(json.dumps({"message": "Hello", "model": "gemini-flash"}))
            events = []
            for _ in range(20):  # collect up to 20 messages
                data = ws.receive_text()
                event = json.loads(data)
                events.append(event)
                if event["type"] == "done":
                    break
    types = [e["type"] for e in events]
    assert "token" in types
    assert events[-1]["type"] == "done"
```

- [ ] Run test (should fail):

```bash
pytest tests/test_chat.py -v
# Expected: 404 on /ws/chat
```

### Step 3.2 — Create `app/models/conversation.py`

- [ ] Create `app/models/conversation.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.user import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Step 3.3 — Update `app/models/user.py` to import Base from shared location

- [ ] Refactor: move `Base` to `app/models/base.py` so all models share it:

```python
# app/models/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

- [ ] Update `app/models/user.py` to import `Base` from `app.models.base`.
- [ ] Update `app/models/conversation.py` to import `Base` from `app.models.base`.
- [ ] Update `app/core/database.py` to import `Base` from `app.models.base`.

### Step 3.4 — Create `app/api/chat.py`

- [ ] Create `app/api/chat.py`:

```python
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError
from app.core.security import decode_token
from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation, Message

router = APIRouter()

MOCK_RESPONSE = "Hello from Mobius! I am your AI assistant ready to help."


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, token: str = Query(...)):
    # Authenticate
    try:
        user_id = decode_token(token)
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            user_message = payload.get("message", "")

            # Persist conversation + user message
            async with AsyncSessionLocal() as session:
                conv = Conversation(user_id=user_id)
                session.add(conv)
                await session.flush()
                session.add(Message(conversation_id=conv.id, role="user", content=user_message))
                await session.commit()
                conv_id = conv.id

            # Stream mock response word by word
            words = MOCK_RESPONSE.split()
            full_response = []
            for word in words:
                chunk = word + " "
                full_response.append(chunk)
                await websocket.send_text(json.dumps({"type": "token", "content": chunk}))
                await asyncio.sleep(0.05)

            # Persist assistant message
            async with AsyncSessionLocal() as session:
                session.add(Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content="".join(full_response).strip()
                ))
                await session.commit()

            await websocket.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        pass
```

### Step 3.5 — Register the chat router

- [ ] Update `app/api/router.py`:

```python
from fastapi import APIRouter
from app.api import auth, chat

router = APIRouter()
router.include_router(auth.router)
router.include_router(chat.router)
```

### Step 3.6 — Update `tests/conftest.py` to include conversation models in test DB

- [ ] Import `Conversation` and `Message` in conftest so their tables are created:

```python
from app.models import user, conversation  # noqa: F401 — ensures tables registered with Base
```

### Step 3.7 — Run tests (should pass)

```bash
pytest tests/test_chat.py tests/test_auth.py tests/test_health.py -v
# Expected: all PASSED
```

### Step 3.8 — Commit

```bash
git add .
git commit -m "feat: add WebSocket chat endpoint with mock streaming and conversation persistence"
```

---

## Task 4: LiteLLM Agent Engine (Gemini Flash)

**Goal:** Replace the mock streaming with a real LiteLLM call to Gemini Flash. The agent engine is a standalone async function that can be unit-tested with mocks.

### Step 4.1 — Write failing tests first

- [ ] Create `tests/test_agent_engine.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

async def test_run_agent_calls_on_token(monkeypatch):
    """run_agent should call on_token for each streamed chunk."""
    from app.agents.engine import run_agent

    fake_chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello "))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content="world"))]),
    ]

    async def fake_stream(*args, **kwargs):
        for chunk in fake_chunks:
            yield chunk

    with patch("app.agents.engine.litellm.acompletion", return_value=fake_stream()):
        tokens = []
        await run_agent(
            message="hi",
            model="gemini/gemini-2.0-flash",
            api_key=None,
            tools=[],
            on_token=lambda t: tokens.append(t)
        )
        assert tokens == ["Hello ", "world"]


async def test_run_agent_uses_user_api_key(monkeypatch):
    """run_agent should pass user api_key to litellm if provided."""
    from app.agents.engine import run_agent

    async def fake_stream(*args, **kwargs):
        assert kwargs.get("api_key") == "user-key-123"
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="ok"))])

    with patch("app.agents.engine.litellm.acompletion", return_value=fake_stream()):
        await run_agent(
            message="hi",
            model="gemini/gemini-2.0-flash",
            api_key="user-key-123",
            tools=[],
            on_token=lambda t: None
        )
```

- [ ] Run test (should fail):

```bash
pytest tests/test_agent_engine.py -v
# Expected: ImportError — app.agents.engine does not exist
```

### Step 4.2 — Create `app/agents/engine.py`

- [ ] Create `app/agents/__init__.py` (empty).
- [ ] Create `app/agents/tools/__init__.py` (empty).
- [ ] Create `app/agents/engine.py`:

```python
from typing import Callable, Any
import litellm
from app.core.config import settings


async def run_agent(
    message: str,
    model: str,
    api_key: str | None,
    tools: list,
    on_token: Callable[[str], Any],
) -> str:
    """
    Stream a single-turn LLM response via LiteLLM.
    Calls on_token(chunk) for each streamed token.
    Returns the full concatenated response.
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": True,
    }

    # Use user-supplied key, or fall back to server Gemini key
    if api_key:
        kwargs["api_key"] = api_key
    else:
        kwargs["api_key"] = settings.GEMINI_API_KEY

    full_response = []
    async for chunk in await litellm.acompletion(**kwargs):
        delta = chunk.choices[0].delta.content
        if delta:
            on_token(delta)
            full_response.append(delta)

    return "".join(full_response)
```

### Step 4.3 — Wire LiteLLM engine into the WebSocket handler

- [ ] Update `app/api/chat.py` to call `run_agent` instead of the mock loop:

```python
# Replace the mock streaming block with:
from app.agents.engine import run_agent

# Inside the while loop, after persisting user message:
model = payload.get("model", "gemini/gemini-2.0-flash")
full_response_parts = []

async def send_token(chunk: str):
    full_response_parts.append(chunk)
    await websocket.send_text(json.dumps({"type": "token", "content": chunk}))

await run_agent(
    message=user_message,
    model=model,
    api_key=None,  # Task 11 will thread user key here
    tools=[],
    on_token=send_token,
)
```

### Step 4.4 — Run tests (should pass)

```bash
pytest tests/test_agent_engine.py -v
# Expected: all PASSED
```

### Step 4.5 — Commit

```bash
git add .
git commit -m "feat: integrate LiteLLM streaming into agent engine and WebSocket handler"
```

---

## Task 5: LangGraph Tool Loop

**Goal:** Wrap the agent engine in a LangGraph StateGraph so the model can decide to call tools (e.g., web_search) before responding, enabling multi-step agentic behavior.

### Step 5.1 — Write failing tests first

- [ ] Add to `tests/test_agent_engine.py`:

```python
async def test_agent_calls_tool_when_needed(monkeypatch):
    """Agent should invoke web_search tool when the LLM requests it."""
    from app.agents.engine import run_agent_with_tools

    tool_called_with = []

    async def mock_web_search(query: str) -> str:
        tool_called_with.append(query)
        return "Paris is the capital of France."

    # First LLM call: returns a tool call request
    # Second LLM call: returns final answer using tool result
    call_count = 0

    async def fake_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate tool call response
            tool_call_chunk = MagicMock()
            tool_call_chunk.choices = [MagicMock(
                finish_reason="tool_calls",
                message=MagicMock(
                    tool_calls=[MagicMock(
                        id="tc1",
                        function=MagicMock(name="web_search", arguments='{"query": "capital of France"}')
                    )],
                    content=None
                )
            )]
            return tool_call_chunk
        else:
            # Final answer
            async def stream():
                yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Paris."))])
            return stream()

    from unittest.mock import patch, MagicMock
    with patch("app.agents.engine.litellm.acompletion", side_effect=fake_acompletion):
        tokens = []
        await run_agent_with_tools(
            message="What is the capital of France?",
            model="gemini/gemini-2.0-flash",
            api_key=None,
            tools={"web_search": mock_web_search},
            on_token=lambda t: tokens.append(t),
        )
    assert "capital of France" in tool_called_with[0]
    assert "Paris" in "".join(tokens)
```

- [ ] Run test (should fail):

```bash
pytest tests/test_agent_engine.py::test_agent_calls_tool_when_needed -v
# Expected: ImportError — run_agent_with_tools not defined
```

### Step 5.2 — Create `app/agents/tools/utils.py`

- [ ] Create `app/agents/tools/utils.py`:

```python
import httpx
from typing import Any


async def web_search(query: str) -> str:
    """Search DuckDuckGo Instant Answer API and return a text summary."""
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
    data = resp.json()
    abstract = data.get("AbstractText") or data.get("Answer") or ""
    if not abstract:
        related = data.get("RelatedTopics", [])
        if related and isinstance(related[0], dict):
            abstract = related[0].get("Text", "No result found.")
    return abstract or "No result found."


async def summarize(text: str, model: str = "gemini/gemini-2.0-flash", api_key: str | None = None) -> str:
    """Summarize text using LLM."""
    import litellm
    from app.core.config import settings
    response = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": f"Summarize the following:\n\n{text}"}],
        api_key=api_key or settings.GEMINI_API_KEY,
    )
    return response.choices[0].message.content or ""
```

### Step 5.3 — Add `run_agent_with_tools` to `app/agents/engine.py`

- [ ] Add to `app/agents/engine.py`:

```python
import json


async def run_agent_with_tools(
    message: str,
    model: str,
    api_key: str | None,
    tools: dict[str, Any],  # name -> async callable
    on_token: Callable[[str], Any],
    max_iterations: int = 5,
) -> str:
    """
    Agentic loop: call LLM, execute any tool calls, feed results back, repeat
    until the model gives a final answer or max_iterations reached.
    """
    from app.core.config import settings as cfg

    effective_key = api_key or cfg.GEMINI_API_KEY
    messages = [{"role": "user", "content": message}]

    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": fn.__doc__ or "",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            }
        }
        for name, fn in tools.items()
    ]

    for _ in range(max_iterations):
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "api_key": effective_key,
        }
        if tool_schemas:
            kwargs["tools"] = tool_schemas

        response = await litellm.acompletion(**kwargs)
        choice = response.choices[0]

        # If model wants to call a tool
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_results = []
            for tc in choice.message.tool_calls:
                fn = tools.get(tc.function.name)
                if fn:
                    args = json.loads(tc.function.arguments)
                    result = await fn(**args)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            messages.append({"role": "assistant", "content": None, "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in choice.message.tool_calls
            ]})
            messages.extend(tool_results)
            continue  # loop back to LLM with tool results

        # Final streaming answer
        kwargs_stream = {**kwargs, "stream": True}
        kwargs_stream.pop("tools", None)
        full = []
        async for chunk in await litellm.acompletion(**kwargs_stream):
            delta = chunk.choices[0].delta.content
            if delta:
                on_token(delta)
                full.append(delta)
        return "".join(full)

    return ""
```

### Step 5.4 — Run tests (all should pass)

```bash
pytest tests/test_agent_engine.py -v
# Expected: all PASSED
```

### Step 5.5 — Commit

```bash
git add .
git commit -m "feat: add LangGraph-style tool loop with web_search support"
```

---

## Task 6: Google Calendar + Gmail Integration

**Goal:** Implement OAuth2 flow for Google APIs and callable functions to create calendar events and send emails, exposed as agent tools.

### Step 6.1 — Write failing tests first

- [ ] Create `tests/test_integrations/test_google.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_store_google_tokens(client):
    """Callback should store OAuth tokens in Redis under oauth:google:{user_id}."""
    import json
    from app.core.config import settings

    # Register user to get an ID
    r = await client.post("/auth/register", json={"email": "g@test.com", "password": "pass"})
    user_id = r.json()["id"]

    fake_tokens = {"access_token": "goog-access", "refresh_token": "goog-refresh"}

    with patch("app.integrations.google.exchange_code_for_tokens", new_callable=AsyncMock, return_value=fake_tokens), \
         patch("app.integrations.google.redis_client") as mock_redis:
        mock_redis.set = AsyncMock()
        response = await client.get(
            f"/integrations/google/callback?code=fake-code&state={user_id}"
        )
        assert response.status_code == 200
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert f"oauth:google:{user_id}" in call_args[0]


async def test_create_calendar_event(monkeypatch):
    """create_calendar_event should POST to Google Calendar API."""
    from app.integrations import google as gmod

    fake_tokens = {"access_token": "tok"}
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "tok"}')
    monkeypatch.setattr(gmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "event-123", "summary": "Test Meeting"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.google.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http

        result = await gmod.create_calendar_event(
            user_id="user-1",
            title="Test Meeting",
            start_dt="2026-05-01T10:00:00",
            end_dt="2026-05-01T11:00:00"
        )
    assert result["id"] == "event-123"


async def test_send_gmail(monkeypatch):
    """send_gmail should POST to Gmail API."""
    from app.integrations import google as gmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "tok"}')
    monkeypatch.setattr(gmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "msg-456"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.google.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http

        result = await gmod.send_gmail(
            user_id="user-1",
            to="recipient@example.com",
            subject="Hello",
            body="Test email body"
        )
    assert result["id"] == "msg-456"
```

- [ ] Run test (should fail):

```bash
pytest tests/test_integrations/test_google.py -v
# Expected: ImportError — app.integrations.google does not exist
```

### Step 6.2 — Create `app/core/redis.py`

- [ ] Create `app/core/redis.py`:

```python
import redis.asyncio as aioredis
from app.core.config import settings

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
```

### Step 6.3 — Create `app/integrations/google.py`

- [ ] Create `app/integrations/__init__.py` (empty).
- [ ] Create `app/integrations/google.py`:

```python
import json
import base64
import email.mime.text
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
```

### Step 6.4 — Create `app/agents/tools/productivity.py`

- [ ] Create `app/agents/tools/productivity.py`:

```python
from app.integrations.google import create_calendar_event as _create_event, send_gmail as _send_gmail


async def create_calendar_event_tool(user_id: str, title: str, start_dt: str, end_dt: str) -> str:
    """Create a Google Calendar event. Returns event ID."""
    result = await _create_event(user_id, title, start_dt, end_dt)
    return f"Event created: {result.get('id')} — {result.get('summary')}"


async def send_gmail_tool(user_id: str, to: str, subject: str, body: str) -> str:
    """Send an email via Gmail. Returns message ID."""
    result = await _send_gmail(user_id, to, subject, body)
    return f"Email sent: {result.get('id')}"
```

### Step 6.5 — Register Google router

- [ ] Update `app/api/integrations.py`:

```python
from fastapi import APIRouter
from app.integrations.google import router as google_router

router = APIRouter()
router.include_router(google_router)
```

- [ ] Update `app/api/router.py` to include integrations router.
- [ ] Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `BASE_URL` to `Settings` in `app/core/config.py`.

### Step 6.6 — Run tests (should pass)

```bash
pytest tests/test_integrations/test_google.py -v
# Expected: all PASSED
```

### Step 6.7 — Commit

```bash
git add .
git commit -m "feat: add Google Calendar and Gmail OAuth integration and agent tools"
```

---

## Task 7: Twitter/X Integration

**Goal:** Implement Twitter OAuth 2.0 PKCE flow and a tool that posts tweets on behalf of the user.

### Step 7.1 — Write failing tests first

- [ ] Create `tests/test_integrations/test_twitter.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_post_tweet(monkeypatch):
    """post_tweet should POST to Twitter API v2."""
    from app.integrations import twitter as tmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "tw-tok"}')
    monkeypatch.setattr(tmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"id": "tweet-789", "text": "Hello!"}}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.twitter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http

        result = await tmod.post_tweet(user_id="user-1", text="Hello!")
    assert result["data"]["id"] == "tweet-789"
```

- [ ] Run test (should fail):

```bash
pytest tests/test_integrations/test_twitter.py -v
# Expected: ImportError — app.integrations.twitter does not exist
```

### Step 7.2 — Create `app/integrations/twitter.py`

- [ ] Create `app/integrations/twitter.py`:

```python
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
```

### Step 7.3 — Add `post_twitter` to `app/agents/tools/social.py`

- [ ] Create `app/agents/tools/social.py`:

```python
from app.integrations.twitter import post_tweet as _post_tweet


async def post_twitter_tool(user_id: str, text: str) -> str:
    """Post a tweet on Twitter/X. Returns tweet ID."""
    result = await _post_tweet(user_id, text)
    tweet_id = result.get("data", {}).get("id", "unknown")
    return f"Tweet posted: {tweet_id}"
```

### Step 7.4 — Register Twitter router in `app/api/integrations.py`

- [ ] Add `from app.integrations.twitter import router as twitter_router` and include it.
- [ ] Add `TWITTER_CLIENT_ID`, `TWITTER_CLIENT_SECRET` to `Settings`.

### Step 7.5 — Run tests (should pass)

```bash
pytest tests/test_integrations/test_twitter.py -v
# Expected: PASSED
```

### Step 7.6 — Commit

```bash
git add .
git commit -m "feat: add Twitter/X OAuth PKCE integration and post_tweet tool"
```

---

## Task 8: Instagram Integration

**Goal:** Implement Facebook Graph API OAuth for Instagram and a tool to post photos with captions.

### Step 8.1 — Write failing tests first

- [ ] Add to `tests/test_integrations/` a file `test_instagram.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_post_instagram_photo(monkeypatch):
    """post_photo should call Graph API to create a container then publish it."""
    from app.integrations import instagram as igmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "ig-tok", "ig_user_id": "123456"}')
    monkeypatch.setattr(igmod, "redis_client", mock_redis)

    container_response = MagicMock()
    container_response.json.return_value = {"id": "container-abc"}
    container_response.raise_for_status = MagicMock()

    publish_response = MagicMock()
    publish_response.json.return_value = {"id": "media-xyz"}
    publish_response.raise_for_status = MagicMock()

    with patch("app.integrations.instagram.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(side_effect=[container_response, publish_response])
        mock_cls.return_value = mock_http

        result = await igmod.post_photo(
            user_id="user-1",
            image_url="https://example.com/photo.jpg",
            caption="My cool post"
        )
    assert result["id"] == "media-xyz"
```

- [ ] Run test (should fail):

```bash
pytest tests/test_integrations/test_instagram.py -v
# Expected: ImportError
```

### Step 8.2 — Create `app/integrations/instagram.py`

- [ ] Create `app/integrations/instagram.py`:

```python
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
```

### Step 8.3 — Add `post_instagram` to `app/agents/tools/social.py`

- [ ] Update `app/agents/tools/social.py`:

```python
from app.integrations.instagram import post_photo as _post_photo

async def post_instagram_tool(user_id: str, image_url: str, caption: str) -> str:
    """Post a photo to Instagram. Returns media ID."""
    result = await _post_photo(user_id, image_url, caption)
    return f"Instagram post created: {result.get('id')}"
```

### Step 8.4 — Run tests (should pass)

```bash
pytest tests/test_integrations/test_instagram.py -v
# Expected: PASSED
```

### Step 8.5 — Commit

```bash
git add .
git commit -m "feat: add Instagram Graph API integration and post_photo tool"
```

---

## Task 9: LinkedIn + Notion Integration

**Goal:** Add OAuth and posting capability for LinkedIn, and OAuth + page creation for Notion.

### Step 9.1 — Write failing tests first

- [ ] Create `tests/test_integrations/test_notion.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


async def test_create_notion_page(monkeypatch):
    """create_notion_page should POST to Notion API."""
    from app.integrations import notion as nmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "notion-tok", "workspace_id": "ws-1"}')
    monkeypatch.setattr(nmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "page-abc", "url": "https://notion.so/page-abc"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.notion.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_http

        result = await nmod.create_notion_page(
            user_id="user-1",
            title="My Page",
            content="Hello from Mobius"
        )
    assert result["id"] == "page-abc"


async def test_post_linkedin(monkeypatch):
    """post_linkedin should POST to LinkedIn UGC Share API."""
    from app.integrations import linkedin as lmod

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=b'{"access_token": "li-tok", "person_urn": "urn:li:person:abc"}')
    monkeypatch.setattr(lmod, "redis_client", mock_redis)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "share-xyz"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.linkedin.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_http

        result = await lmod.post_linkedin(user_id="user-1", text="Hello LinkedIn!")
    assert result["id"] == "share-xyz"
```

- [ ] Run test (should fail):

```bash
pytest tests/test_integrations/test_notion.py -v
# Expected: ImportError
```

### Step 9.2 — Create `app/integrations/notion.py`

- [ ] Create `app/integrations/notion.py`:

```python
import json
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
    import base64
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
```

### Step 9.3 — Create `app/integrations/linkedin.py`

- [ ] Create `app/integrations/linkedin.py`:

```python
import json
import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.redis import redis_client

router = APIRouter(prefix="/integrations/linkedin", tags=["linkedin"])

LI_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LI_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "r_liteprofile w_member_social"


@router.get("/authorize")
async def linkedin_authorize(user_id: str):
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": f"{settings.BASE_URL}/integrations/linkedin/callback",
        "scope": SCOPES,
        "state": user_id,
    }
    url = LI_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback")
async def linkedin_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(LI_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{settings.BASE_URL}/integrations/linkedin/callback",
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "client_secret": settings.LINKEDIN_CLIENT_SECRET,
        })
        resp.raise_for_status()
        tokens = resp.json()
        access_token = tokens["access_token"]

        # Get person URN
        me_resp = await client.get(
            "https://api.linkedin.com/v2/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        me_resp.raise_for_status()
        person_id = me_resp.json()["id"]

    await redis_client.set(f"oauth:linkedin:{state}", json.dumps({
        "access_token": access_token,
        "person_urn": f"urn:li:person:{person_id}",
    }))
    return {"status": "connected", "user_id": state}


async def post_linkedin(user_id: str, text: str) -> dict:
    raw = await redis_client.get(f"oauth:linkedin:{user_id}")
    if not raw:
        raise ValueError(f"No LinkedIn tokens for user {user_id}")
    data = json.loads(raw)
    token = data["access_token"]
    person_urn = data["person_urn"]

    share_body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=share_body,
        )
        resp.raise_for_status()
        return resp.json()
```

### Step 9.4 — Update `app/agents/tools/social.py` and `productivity.py`

- [ ] Add `post_linkedin_tool` to `social.py`:

```python
from app.integrations.linkedin import post_linkedin as _post_linkedin

async def post_linkedin_tool(user_id: str, text: str) -> str:
    """Post to LinkedIn. Returns share ID."""
    result = await _post_linkedin(user_id, text)
    return f"LinkedIn post created: {result.get('id')}"
```

- [ ] Add `create_notion_page_tool` to `productivity.py`:

```python
from app.integrations.notion import create_notion_page as _create_notion

async def create_notion_page_tool(user_id: str, title: str, content: str) -> str:
    """Create a Notion page. Returns page URL."""
    result = await _create_notion(user_id, title, content)
    return f"Notion page created: {result.get('url')}"
```

### Step 9.5 — Register LinkedIn and Notion routers

- [ ] Update `app/api/integrations.py` to include both routers.
- [ ] Add `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET` to `Settings`.

### Step 9.6 — Run tests (should pass)

```bash
pytest tests/test_integrations/test_notion.py -v
# Expected: all PASSED
```

### Step 9.7 — Commit

```bash
git add .
git commit -m "feat: add LinkedIn and Notion OAuth integrations and agent tools"
```

---

## Task 10: Scheduled Automations

**Goal:** Allow users to define prompts that run on a cron schedule. APScheduler picks them up at startup, uses Redis locks to prevent duplicate runs across instances.

### Step 10.1 — Write failing tests first

- [ ] Create `tests/test_automations.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch


async def _auth_headers(client) -> dict:
    await client.post("/auth/register", json={"email": "auto@test.com", "password": "pass"})
    r = await client.post("/auth/token", json={"email": "auto@test.com", "password": "pass"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_automation(client):
    headers = await _auth_headers(client)
    response = await client.post("/automations", headers=headers, json={
        "prompt": "Post good morning on Twitter",
        "cron_expr": "0 8 * * *",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["prompt"] == "Post good morning on Twitter"
    assert data["cron_expr"] == "0 8 * * *"
    assert data["active"] is True
    assert "id" in data


async def test_list_automations(client):
    headers = await _auth_headers(client)
    await client.post("/automations", headers=headers, json={
        "prompt": "Daily digest", "cron_expr": "0 9 * * *"
    })
    response = await client.get("/automations", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


async def test_delete_automation(client):
    headers = await _auth_headers(client)
    r = await client.post("/automations", headers=headers, json={
        "prompt": "Weekly report", "cron_expr": "0 10 * * 1"
    })
    auto_id = r.json()["id"]
    del_resp = await client.delete(f"/automations/{auto_id}", headers=headers)
    assert del_resp.status_code == 204
```

- [ ] Run test (should fail):

```bash
pytest tests/test_automations.py -v
# Expected: 404 on /automations
```

### Step 10.2 — Create `app/models/automation.py`

- [ ] Create `app/models/automation.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ScheduledAutomation(Base):
    __tablename__ = "scheduled_automations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    cron_expr: Mapped[str] = mapped_column(String, nullable=False)
    last_run: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Step 10.3 — Create `app/api/automations.py`

- [ ] Create `app/api/automations.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from jose import JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.database import get_session
from app.core.security import decode_token
from app.models.automation import ScheduledAutomation

router = APIRouter(prefix="/automations", tags=["automations"])
bearer = HTTPBearer()


async def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        return decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class AutomationCreate(BaseModel):
    prompt: str
    cron_expr: str


class AutomationResponse(BaseModel):
    id: str
    prompt: str
    cron_expr: str
    active: bool
    user_id: str


@router.post("", response_model=AutomationResponse, status_code=201)
async def create_automation(
    body: AutomationCreate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    auto = ScheduledAutomation(user_id=user_id, prompt=body.prompt, cron_expr=body.cron_expr)
    session.add(auto)
    await session.commit()
    await session.refresh(auto)
    return AutomationResponse(id=auto.id, prompt=auto.prompt, cron_expr=auto.cron_expr, active=auto.active, user_id=auto.user_id)


@router.get("", response_model=list[AutomationResponse])
async def list_automations(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(ScheduledAutomation).where(ScheduledAutomation.user_id == user_id))
    autos = result.scalars().all()
    return [AutomationResponse(id=a.id, prompt=a.prompt, cron_expr=a.cron_expr, active=a.active, user_id=a.user_id) for a in autos]


@router.delete("/{automation_id}", status_code=204)
async def delete_automation(
    automation_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    auto = await session.get(ScheduledAutomation, automation_id)
    if not auto or auto.user_id != user_id:
        raise HTTPException(status_code=404, detail="Automation not found")
    await session.delete(auto)
    await session.commit()
```

### Step 10.4 — Add APScheduler background scheduler to `app/main.py`

- [ ] Update `app/main.py` lifespan to start scheduler:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from app.models.automation import ScheduledAutomation
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.agents.engine import run_agent
from app.core.config import settings
import asyncio

scheduler = AsyncIOScheduler()


async def run_automation(automation_id: str, prompt: str):
    """Run a scheduled automation with Redis lock to prevent duplicate execution."""
    lock_key = f"lock:automation:{automation_id}"
    acquired = await redis_client.set(lock_key, "1", nx=True, ex=300)
    if not acquired:
        return  # Already running elsewhere

    try:
        await run_agent(
            message=prompt,
            model="gemini/gemini-2.0-flash",
            api_key=None,
            tools=[],
            on_token=lambda t: None,  # Fire-and-forget for scheduled runs
        )
        async with AsyncSessionLocal() as session:
            auto = await session.get(ScheduledAutomation, automation_id)
            if auto:
                from datetime import datetime
                auto.last_run = datetime.utcnow()
                await session.commit()
    finally:
        await redis_client.delete(lock_key)


async def load_automations():
    """Load all active automations from DB and schedule them."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScheduledAutomation).where(ScheduledAutomation.active == True)
        )
        automations = result.scalars().all()

    for auto in automations:
        try:
            trigger = CronTrigger.from_crontab(auto.cron_expr)
            scheduler.add_job(
                run_automation,
                trigger=trigger,
                args=[auto.id, auto.prompt],
                id=auto.id,
                replace_existing=True,
            )
        except Exception as e:
            print(f"Failed to schedule automation {auto.id}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await load_automations()
    scheduler.start()
    yield
    scheduler.shutdown()
```

### Step 10.5 — Register automations router and update `conftest.py`

- [ ] Update `app/api/router.py` to include `automations.router`.
- [ ] Update `tests/conftest.py` to import `app.models.automation` for table creation.

### Step 10.6 — Run tests (should pass)

```bash
pytest tests/test_automations.py -v
# Expected: all PASSED
```

### Step 10.7 — Commit

```bash
git add .
git commit -m "feat: add scheduled automations CRUD with APScheduler and Redis locking"
```

---

## Task 11: User API Key Support

**Goal:** Allow users to store their own API keys (Claude, GPT-4o, etc.) encrypted in the database. The agent engine uses the user key if available, falling back to the server Gemini key.

### Step 11.1 — Write failing tests first

- [ ] Add to `tests/test_auth.py`:

```python
async def test_store_and_use_api_key(client):
    """User can store an API key and it is passed to the agent engine."""
    import json

    # Register and get token
    await client.post("/auth/register", json={"email": "keyuser@test.com", "password": "pass"})
    r = await client.post("/auth/token", json={"email": "keyuser@test.com", "password": "pass"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Store API key
    resp = await client.put("/auth/api-keys", headers=headers, json={
        "provider": "openai",
        "key": "sk-test-12345"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "stored"

    # Retrieve and verify (via a dedicated endpoint for listing providers)
    list_resp = await client.get("/auth/api-keys", headers=headers)
    assert list_resp.status_code == 200
    providers = list_resp.json()["providers"]
    assert "openai" in providers


async def test_engine_uses_user_key(monkeypatch):
    """run_agent should pick up user-provided key and pass it to LiteLLM."""
    from app.agents.engine import run_agent
    from unittest.mock import patch, MagicMock

    captured_kwargs = {}

    async def fake_stream(**kwargs):
        captured_kwargs.update(kwargs)
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="done"))])

    with patch("app.agents.engine.litellm.acompletion", return_value=fake_stream()):
        await run_agent(
            message="test",
            model="openai/gpt-4o",
            api_key="sk-user-key",
            tools=[],
            on_token=lambda t: None,
        )
    assert captured_kwargs.get("api_key") == "sk-user-key"
```

- [ ] Run test (should fail):

```bash
pytest tests/test_auth.py::test_store_and_use_api_key -v
# Expected: 404 on PUT /auth/api-keys
```

### Step 11.2 — Update `app/api/auth.py` with API key endpoints

- [ ] Add to `app/api/auth.py`:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import encrypt_api_key, decrypt_api_key, decode_token

bearer = HTTPBearer()


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
    provider: str  # "openai" | "anthropic" | "gemini"
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
```

### Step 11.3 — Thread user API key through the WebSocket handler

- [ ] Update `app/api/chat.py` to:
  1. Load user from DB after authentication.
  2. Detect the requested model's provider.
  3. Decrypt and pass the user's key to `run_agent` if available.

```python
# Inside ws_chat, after decoding token:
from app.core.security import decrypt_api_key
from sqlalchemy import select as sa_select
from app.models.user import User as UserModel

async with AsyncSessionLocal() as session:
    db_user = await session.get(UserModel, user_id)

# Then when calling run_agent:
provider = model.split("/")[0]  # e.g. "openai" from "openai/gpt-4o"
user_key = None
if db_user and db_user.api_keys and provider in db_user.api_keys:
    user_key = decrypt_api_key(db_user.api_keys[provider])

await run_agent(
    message=user_message,
    model=model,
    api_key=user_key,
    tools=[],
    on_token=send_token,
)
```

### Step 11.4 — Run all tests (full suite)

```bash
pytest -v
# Expected: all tests PASSED
# Summary example:
# 15 passed in X.XXs
```

### Step 11.5 — Commit

```bash
git add .
git commit -m "feat: add encrypted user API key storage and per-user LiteLLM key injection"
```

---

## Full Test Suite Commands Reference

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing -v

# Run a single task's tests
pytest tests/test_auth.py -v
pytest tests/test_chat.py -v
pytest tests/test_agent_engine.py -v
pytest tests/test_integrations/ -v
pytest tests/test_automations.py -v

# Run in Docker (against real Postgres + Redis)
docker compose up -d postgres redis
DATABASE_URL=postgresql+asyncpg://mobius:mobius@localhost:5432/mobius \
REDIS_URL=redis://localhost:6379/0 \
pytest -v
```

---

## Settings Reference (`app/core/config.py` final state)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://mobius:mobius@localhost:5432/mobius"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production-32-bytes!!"
    GEMINI_API_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    BASE_URL: str = "http://localhost:8000"

    # Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Twitter/X
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""

    # Instagram / Facebook
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""

    # LinkedIn
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # Notion
    NOTION_CLIENT_ID: str = ""
    NOTION_CLIENT_SECRET: str = ""
```

---

## Implementation Notes

### OAuth State Security
The `state` parameter in all OAuth flows is currently the raw `user_id`. For production, replace with a signed HMAC token that encodes `user_id + timestamp`, validated on callback. This prevents CSRF attacks.

### Token Refresh
All integration modules store `refresh_token` but do not implement auto-refresh. Before production, add a `_refresh_token(provider, user_id)` helper called on 401 responses from any integration API.

### WebSocket Reconnection
The Flutter app must implement exponential backoff reconnection. The server does not implement connection tracking or message replay. For resilience, consider adding a Redis pub/sub layer so WebSocket handlers can broadcast across multiple server instances.

### Alembic Migrations
Task 1 uses `metadata.create_all` for MVP simplicity. Before first production deploy, add Alembic:
```bash
pip install alembic
alembic init alembic
# Configure alembic/env.py to use async engine
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### LiteLLM Model String Mapping
| User-facing model name | LiteLLM model string |
|------------------------|---------------------|
| `gemini-flash` | `gemini/gemini-2.0-flash` |
| `gpt-4o` | `openai/gpt-4o` |
| `claude-3-5-sonnet` | `anthropic/claude-3-5-sonnet-20241022` |

Map these in `app/agents/engine.py` before passing to LiteLLM.

### Device Tools (`app/agents/tools/device.py`)
These tools (`open_app`, `take_screenshot`, `read_screen`) are invoked by the server but executed by the Flutter app via a reverse WebSocket command channel. Implement as stubs that send a `{"type": "device_command", "action": "..."}` message over the WS connection and await a `{"type": "device_result", ...}` response.
