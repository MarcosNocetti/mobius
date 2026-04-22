import json
import logging
from typing import Callable, Any, Awaitable
import litellm
from app.core.config import settings

logger = logging.getLogger("mobius.engine")


async def run_agent(
    message: str,
    model: str,
    api_key: str | None,
    tools: list,
    on_token: Callable[[str], Awaitable[Any]],
) -> str:
    effective_key = api_key or settings.GEMINI_API_KEY

    logger.info(f"[engine] model={model!r} api_key={'SET' if effective_key else 'EMPTY'}")

    if not effective_key:
        logger.warning("[engine] No API key available — call will likely fail")

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": True,
        "api_key": effective_key,
    }

    full_response = []
    token_count = 0
    try:
        async for chunk in await litellm.acompletion(**kwargs):
            delta = chunk.choices[0].delta.content
            if delta:
                token_count += 1
                await on_token(delta)          # ← was missing await
                full_response.append(delta)
    except Exception as e:
        logger.error(f"[engine] LiteLLM error: {e}")
        raise

    logger.info(f"[engine] Done — {token_count} tokens")
    return "".join(full_response)


async def run_agent_with_tools(
    message: str,
    model: str,
    api_key: str | None,
    tools: dict[str, Any],
    on_token: Callable[[str], Awaitable[Any]],
    max_iterations: int = 5,
) -> str:
    effective_key = api_key or settings.GEMINI_API_KEY
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
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.message.tool_calls
                ]
            })
            messages.extend(tool_results)
            kwargs_stream = {**kwargs, "stream": True, "messages": messages}
            kwargs_stream.pop("tools", None)
            full = []
            async for chunk in await litellm.acompletion(**kwargs_stream):
                delta = chunk.choices[0].delta.content
                if delta:
                    await on_token(delta)
                    full.append(delta)
            return "".join(full)

        content = choice.message.content or ""
        if content:
            await on_token(content)
        return content

    return ""
