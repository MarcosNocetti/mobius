import ast
import asyncio
import logging
from datetime import datetime
from app.automation.context import AutomationContext

logger = logging.getLogger("mobius.sandbox")

SAFE_BUILTINS = {
    "True": True, "False": False, "None": None,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter,
    "min": min, "max": max, "sum": sum, "sorted": sorted,
    "abs": abs, "round": round,
    "isinstance": isinstance, "type": type,
    "print": print,  # Redirected to ctx.log in practice
    "asyncio": asyncio,  # Allow async primitives in scripts
}

FORBIDDEN_NODES = {
    ast.Import, ast.ImportFrom,  # No imports
}


def validate_script(source: str) -> list[str]:
    """Validate script source for safety. Returns list of errors."""
    errors = []
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]

    for node in ast.walk(tree):
        if type(node) in FORBIDDEN_NODES:
            errors.append(f"Forbidden: {type(node).__name__} (no imports allowed)")
    return errors


async def execute_script(source: str, ctx: AutomationContext, timeout: int = 300) -> str:
    """Execute an automation script with the given context. Returns output."""
    errors = validate_script(source)
    if errors:
        raise ValueError(f"Script validation failed: {'; '.join(errors)}")

    # Compile the script
    code = compile(source, "<automation>", "exec")

    # Build globals with ctx and safe builtins
    script_globals = {"__builtins__": SAFE_BUILTINS, "ctx": ctx}

    # Execute with timeout
    async def run():
        exec(code, script_globals)
        # If the script defines a `run` function, call it
        if "run" in script_globals and callable(script_globals["run"]):
            result = script_globals["run"](ctx)
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                ctx.set_output(str(result))

    try:
        await asyncio.wait_for(run(), timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Script execution exceeded {timeout}s timeout")

    return ctx._output or "Completed successfully"
