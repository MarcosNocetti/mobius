import json
import logging
import itertools
from typing import Callable, Any, Awaitable
import litellm
from app.core.config import settings

logger = logging.getLogger("mobius.engine")

# Round-robin key rotation for Gemini free tier
_key_cycle = None


def _get_gemini_key() -> str:
    """Get next Gemini API key from the rotation pool."""
    global _key_cycle
    keys_str = settings.GEMINI_API_KEYS
    if keys_str:
        keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        if keys:
            if _key_cycle is None:
                _key_cycle = itertools.cycle(keys)
            return next(_key_cycle)
    return settings.GEMINI_API_KEY


async def run_agent(
    message: str,
    model: str,
    api_key: str | None,
    tools: list,
    on_token: Callable[[str], Awaitable[Any]],
) -> str:
    """Simple single-turn streaming (no tools)."""
    effective_key = api_key or _get_gemini_key()
    logger.info(f"[engine] model={model!r} api_key={'SET' if effective_key else 'EMPTY'}")

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": True,
        "api_key": effective_key,
    }

    full_response = []
    try:
        async for chunk in await litellm.acompletion(**kwargs):
            delta = chunk.choices[0].delta.content
            if delta:
                await on_token(delta)
                full_response.append(delta)
    except Exception as e:
        logger.error(f"[engine] LiteLLM error: {e}")
        raise

    logger.info(f"[engine] Done — {len(full_response)} chunks")
    return "".join(full_response)


async def _call_with_retry(model: str, api_key: str | None, max_retries: int = 5, **kwargs):
    """Call litellm.acompletion with key rotation on 429."""
    last_err = None
    # First try user key, then rotate through server keys
    keys_to_try = []
    if api_key:
        keys_to_try.append(api_key)
    keys_str = settings.GEMINI_API_KEYS
    if keys_str:
        for k in keys_str.split(","):
            k = k.strip()
            if k and k not in keys_to_try:
                keys_to_try.append(k)
    if not keys_to_try:
        keys_to_try.append(settings.GEMINI_API_KEY)

    for i, key in enumerate(keys_to_try[:max_retries]):
        try:
            return await litellm.acompletion(api_key=key, model=model, **kwargs)
        except litellm.exceptions.RateLimitError as e:
            logger.warning(f"[engine] key ...{key[-6:]} rate limited ({i+1}/{len(keys_to_try)})")
            last_err = e
            continue
    raise last_err


async def run_agent_with_tools(
    message: str,
    model: str,
    api_key: str | None,
    tool_registry: dict[str, dict],  # {name: {"fn": callable, "schema": dict}}
    on_token: Callable[[str], Awaitable[Any]],
    max_iterations: int = 5,
) -> str:
    """
    Agentic loop: call LLM with tools, execute tool calls, feed results back.
    Streams the final text answer.
    """
    effective_key = api_key
    messages = [{"role": "user", "content": message}]

    tool_schemas = [t["schema"] for t in tool_registry.values()]
    tool_fns = {name: t["fn"] for name, t in tool_registry.items()}

    logger.info(f"[engine] agent loop: model={model!r} tools={list(tool_fns.keys())}")

    for iteration in range(max_iterations):
        extra = {}
        if tool_schemas:
            extra["tools"] = tool_schemas

        response = await _call_with_retry(model, effective_key, messages=messages, **extra)
        choice = response.choices[0]

        logger.info(f"[engine] finish_reason={choice.finish_reason!r} tool_calls={bool(choice.message.tool_calls)} content_len={len(choice.message.content or '')}")

        # If model wants to call tools
        if choice.message.tool_calls:
            logger.info(f"[engine] iteration {iteration}: {len(choice.message.tool_calls)} tool call(s)")

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ],
            })

            # Execute each tool call
            for tc in choice.message.tool_calls:
                fn = tool_fns.get(tc.function.name)
                if fn:
                    try:
                        args = json.loads(tc.function.arguments)
                        logger.info(f"[engine] calling {tc.function.name}({args})")
                        result = await fn(**args)
                        logger.info(f"[engine] {tc.function.name} returned: {result}")
                        content = str(result) if not isinstance(result, str) else result
                    except Exception as e:
                        logger.error(f"[engine] tool {tc.function.name} failed: {e}")
                        content = f"Error: {e}"
                else:
                    content = f"Error: unknown tool '{tc.function.name}'"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                })

            # Continue loop — LLM will see tool results and decide next step
            continue

        # Final answer (no tool calls) — stream it
        content = choice.message.content or ""
        if content:
            await on_token(content)
        logger.info(f"[engine] final answer, {len(content)} chars")
        return content

    logger.warning("[engine] max iterations reached")
    return ""
