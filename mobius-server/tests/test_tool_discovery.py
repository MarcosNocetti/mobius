import pytest
from app.agents.tools.decorator import tool_action


def test_tool_action_registers_metadata():
    @tool_action(
        name="test_tool",
        description="A test tool",
        integration="test",
        params={
            "arg1": {"type": "string", "description": "First arg"},
        },
    )
    async def my_tool(user_id: str, arg1: str) -> str:
        return f"result: {arg1}"

    assert hasattr(my_tool, "_tool_meta")
    assert my_tool._tool_meta.name == "test_tool"
    assert my_tool._tool_meta.description == "A test tool"
    assert my_tool._tool_meta.integration == "test"


def test_tool_meta_generates_openai_schema():
    @tool_action(
        name="create_thing",
        description="Creates a thing",
        integration="test",
        params={
            "title": {"type": "string", "description": "Thing title"},
            "count": {"type": "integer", "description": "How many"},
        },
    )
    async def create_thing(user_id: str, title: str, count: int) -> str:
        return "done"

    schema = create_thing._tool_meta.to_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "create_thing"
    assert "title" in schema["function"]["parameters"]["properties"]
    assert "count" in schema["function"]["parameters"]["properties"]
    assert "user_id" not in schema["function"]["parameters"]["properties"]


def test_tool_meta_bind_injects_user_id():
    @tool_action(
        name="bound_tool",
        description="Test binding",
        integration="test",
        params={"msg": {"type": "string", "description": "Message"}},
    )
    async def send(user_id: str, msg: str) -> str:
        return f"{user_id}:{msg}"

    bound = send._tool_meta.bind("user-123", send)
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(bound(msg="hello"))
    assert result == "user-123:hello"
