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

    # Use user-supplied key, or fall back to server Gemini key
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
