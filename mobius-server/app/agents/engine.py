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
    """Simple single-turn streaming (no tools)."""
    effective_key = api_key or settings.GEMINI_API_KEY
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
    effective_key = api_key or settings.GEMINI_API_KEY
    messages = [{"role": "user", "content": message}]

    tool_schemas = [t["schema"] for t in tool_registry.values()]
    tool_fns = {name: t["fn"] for name, t in tool_registry.items()}

    logger.info(f"[engine] agent loop: model={model!r} tools={list(tool_fns.keys())}")

    for iteration in range(max_iterations):
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "api_key": effective_key,
        }
        if tool_schemas:
            kwargs["tools"] = tool_schemas

        response = await litellm.acompletion(**kwargs)
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
