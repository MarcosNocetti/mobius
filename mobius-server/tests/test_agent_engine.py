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


async def test_agent_calls_tool_when_needed():
    """Agent should invoke web_search tool when the LLM requests it."""
    from app.agents.engine import run_agent_with_tools
    from unittest.mock import patch, MagicMock, AsyncMock

    tool_called_with = []

    async def mock_web_search(query: str) -> str:
        tool_called_with.append(query)
        return "Paris is the capital of France."

    call_count = 0

    async def fake_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate tool call response (non-streaming)
            tool_call_mock = MagicMock()
            tool_call_mock.id = "tc1"
            tool_call_mock.function.name = "web_search"
            tool_call_mock.function.arguments = '{"query": "capital of France"}'

            choice = MagicMock()
            choice.finish_reason = "tool_calls"
            choice.message.tool_calls = [tool_call_mock]
            choice.message.content = None

            response = MagicMock()
            response.choices = [choice]
            return response
        else:
            # Final streaming answer
            async def stream():
                yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Paris."))])
            return stream()

    with patch("app.agents.engine.litellm.acompletion", side_effect=fake_acompletion):
        tokens = []
        await run_agent_with_tools(
            message="What is the capital of France?",
            model="gemini/gemini-2.0-flash",
            api_key=None,
            tools={"web_search": mock_web_search},
            on_token=lambda t: tokens.append(t),
        )
    assert len(tool_called_with) >= 1
    assert "capital of France" in tool_called_with[0].lower() or "France" in tool_called_with[0]
    assert "Paris" in "".join(tokens)
