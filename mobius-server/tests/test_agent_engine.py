import pytest
from unittest.mock import patch, MagicMock


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

    captured = {}

    async def fake_acompletion(*args, **kwargs):
        captured.update(kwargs)

        async def _gen():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="ok"))])

        return _gen()

    with patch("app.agents.engine.litellm.acompletion", side_effect=fake_acompletion):
        await run_agent(
            message="hi",
            model="gemini/gemini-2.0-flash",
            api_key="user-key-123",
            tools=[],
            on_token=lambda t: None
        )
    assert captured.get("api_key") == "user-key-123"
