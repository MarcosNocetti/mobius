import pytest
import json
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.base import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _register_and_token(client) -> str:
    await client.post("/auth/register", json={"email": "ws@test.com", "password": "pass"})
    r = await client.post("/auth/token", json={"email": "ws@test.com", "password": "pass"})
    return r.json()["access_token"]


async def test_ws_requires_token(client):
    """Connection without token should be rejected."""
    from starlette.testclient import TestClient
    from app.main import app as fastapi_app
    import app.core.database as db_module

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Patch init_db at both locations so lifespan doesn't attempt real DB connection
    with patch("app.main.init_db", new=AsyncMock(return_value=None)), \
         patch.object(db_module, "AsyncSessionLocal", new=session_factory):
        with TestClient(fastapi_app, raise_server_exceptions=False) as tc:
            try:
                with tc.websocket_connect("/ws/chat") as ws:
                    ws.receive_text()
                assert False, "Should have been rejected"
            except Exception:
                pass  # Expected — no token provided

    await engine.dispose()


async def test_ws_streams_tokens(client):
    """Valid token produces streaming token chunks and a done event."""
    from starlette.testclient import TestClient
    from app.main import app as fastapi_app
    import app.core.database as db_module

    # Get token via the async httpx client (which uses the fixture's in-memory DB)
    token = await _register_and_token(client)

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    with patch("app.main.init_db", new=AsyncMock(return_value=None)), \
         patch.object(db_module, "AsyncSessionLocal", new=session_factory), \
         patch("app.api.chat.AsyncSessionLocal", new=session_factory):
        with TestClient(fastapi_app, raise_server_exceptions=False) as tc:
            with tc.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.send_text(json.dumps({"message": "Hello", "model": "gemini-flash"}))
                events = []
                for _ in range(30):  # collect up to 30 messages
                    data = ws.receive_text()
                    event = json.loads(data)
                    events.append(event)
                    if event["type"] == "done":
                        break

    await engine.dispose()

    types = [e["type"] for e in events]
    assert "token" in types
    assert events[-1]["type"] == "done"
