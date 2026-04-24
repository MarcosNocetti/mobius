import ast
import asyncio
import json
import logging
import math
import re
import time
import datetime as _datetime
from app.automation.context import AutomationContext

logger = logging.getLogger("mobius.sandbox")

# Safe modules available to automation scripts (no imports needed)
SAFE_MODULES = {
    "datetime": _datetime,
    "json": json,
    "asyncio": asyncio,
    "time": time,
    "re": re,
    "math": math,
}

SAFE_BUILTINS = {
    "True": True, "False": False, "None": None,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter,
    "min": min, "max": max, "sum": sum, "sorted": sorted,
    "abs": abs, "round": round,
    "isinstance": isinstance, "type": type,
    "print": print,
}

# Only allow importing safe modules
ALLOWED_IMPORTS = {"datetime", "json", "asyncio", "time", "re", "math"}


def validate_script(source: str) -> list[str]:
    """Validate script source for safety. Returns list of errors."""
    errors = []
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_IMPORTS:
                    errors.append(f"Forbidden import: '{alias.name}'. Allowed: {ALLOWED_IMPORTS}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] not in ALLOWED_IMPORTS:
                errors.append(f"Forbidden import: '{node.module}'. Allowed: {ALLOWED_IMPORTS}")
    return errors


async def execute_script(source: str, ctx: AutomationContext, timeout: int = 300) -> str:
    """Execute an automation script with the given context. Returns output."""
    errors = validate_script(source)
    if errors:
        raise ValueError(f"Script validation failed: {'; '.join(errors)}")

    code = compile(source, "<automation>", "exec")

    # Safe __import__ that only allows whitelisted modules
    def safe_import(name, *args, **kwargs):
        if name in SAFE_MODULES:
            return SAFE_MODULES[name]
        raise ImportError(f"Import '{name}' not allowed. Available: {list(SAFE_MODULES.keys())}")

    builtins_with_import = {**SAFE_BUILTINS, "__import__": safe_import}

    # Build globals: builtins + safe modules + ctx
    script_globals = {
        "__builtins__": builtins_with_import,
        "ctx": ctx,
        **SAFE_MODULES,  # datetime, json, asyncio available without import
    }

    async def run():
        exec(code, script_globals)
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
