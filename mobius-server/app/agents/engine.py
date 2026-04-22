import json
from typing import Callable, Any
import litellm
from app.core.config import settings


async def run_agent(
    message: str,
    model: str,
    api_key: str | None,
    tools: list,
    on_token: Callable[[str], Any],
) -> str:
    """
    Stream a single-turn LLM response via LiteLLM.
    Calls on_token(chunk) for each streamed token.
    Returns the full concatenated response.
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": True,
    }

    if api_key:
        kwargs["api_key"] = api_key
    else:
        kwargs["api_key"] = settings.GEMINI_API_KEY

    full_response = []
    async for chunk in await litellm.acompletion(**kwargs):
        delta = chunk.choices[0].delta.content
        if delta:
            on_token(delta)
            full_response.append(delta)

    return "".join(full_response)


async def run_agent_with_tools(
    message: str,
    model: str,
    api_key: str | None,
    tools: dict[str, Any],  # name -> async callable
    on_token: Callable[[str], Any],
    max_iterations: int = 5,
) -> str:
    """
    Agentic loop: call LLM, execute any tool calls, feed results back, repeat
    until the model gives a final answer or max_iterations reached.
    """
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

        # If model wants to call a tool
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
            # Final streaming answer after tool results
            kwargs_stream = {**kwargs, "stream": True, "messages": messages}
            kwargs_stream.pop("tools", None)
            full = []
            async for chunk in await litellm.acompletion(**kwargs_stream):
                delta = chunk.choices[0].delta.content
                if delta:
                    on_token(delta)
                    full.append(delta)
            return "".join(full)

        # Final answer (no tool calls): emit content directly
        content = choice.message.content or ""
        if content:
            on_token(content)
        return content

    return ""
