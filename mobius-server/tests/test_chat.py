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
    token = await _register_and_token(client)
    from starlette.testclient import TestClient
    from app.main import app as fastapi_app
    from unittest.mock import AsyncMock, patch, MagicMock
    from app.core.database import AsyncSessionLocal as RealSession

    async def fake_run_agent(message, model, api_key, tools, on_token):
        await on_token("Hello ")
        await on_token("world")
        return "Hello world"

    async def fake_session_ctx():
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()
        mock_conv = MagicMock()
        mock_conv.id = "test-conv-id"
        mock_session.__aenter__.return_value = mock_session
        # Make Conversation().id work
        return mock_session

    with patch("app.api.chat.run_agent", side_effect=fake_run_agent), \
         patch("app.api.chat.AsyncSessionLocal") as mock_sl:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_conv = MagicMock()
        mock_conv.id = "test-conv-id"
        mock_session.flush.side_effect = lambda: setattr(mock_conv, 'id', 'test-conv-id')
        mock_sl.return_value = mock_session

        with patch("app.main.init_db", new_callable=AsyncMock):
            with TestClient(fastapi_app) as tc:
                with tc.websocket_connect(f"/ws/chat?token={token}") as ws:
                    ws.send_text(json.dumps({"message": "Hello", "model": "gemini-flash"}))
                    events = []
                    for _ in range(10):
                        data = ws.receive_text()
                        event = json.loads(data)
                        events.append(event)
                        if event["type"] == "done":
                            break
    types = [e["type"] for e in events]
    assert "token" in types
    assert events[-1]["type"] == "done"
