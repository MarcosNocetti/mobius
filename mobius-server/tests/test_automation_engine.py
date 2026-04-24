import pytest
from app.automation.context import AutomationContext
from app.automation.sandbox import validate_script, execute_script


def test_validate_script_rejects_imports():
    errors = validate_script("import os")
    assert len(errors) > 0
    assert "import" in errors[0].lower() or "Import" in errors[0]


def test_validate_script_accepts_valid():
    errors = validate_script("async def run(ctx):\n    ctx.log('hello')\n    return 'done'")
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_execute_simple_script():
    ctx = AutomationContext(user_id="test", automation_id="test-1")
    result = await execute_script(
        "async def run(ctx):\n    return 'hello world'",
        ctx
    )
    assert result == "hello world"


@pytest.mark.asyncio
async def test_execute_script_with_ctx_log():
    ctx = AutomationContext(user_id="test", automation_id="test-2")
    await execute_script(
        "async def run(ctx):\n    ctx.log('step 1')\n    ctx.log('step 2')\n    return 'done'",
        ctx
    )
    assert len(ctx._logs) == 2


@pytest.mark.asyncio
async def test_execute_script_rejects_imports():
    ctx = AutomationContext(user_id="test", automation_id="test-3")
    with pytest.raises(ValueError, match="validation failed"):
        await execute_script("import os\nos.system('rm -rf /')", ctx)


@pytest.mark.asyncio
async def test_execute_script_timeout():
    ctx = AutomationContext(user_id="test", automation_id="test-5")
    # Script that runs forever using asyncio.sleep (available via safe builtins)
    script = """
async def run(ctx):
    while True:
        await asyncio.sleep(0.01)
"""
    with pytest.raises(TimeoutError):
        await execute_script(script, ctx, timeout=1)
