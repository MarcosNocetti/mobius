import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("mobius.automation")

# Sao Paulo timezone
SP_TZ = timezone(timedelta(hours=-3))


class AIProxy:
    """Allows automation scripts to call the LLM."""
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    async def ask(self, prompt: str, model: str = "gemini/gemini-2.5-flash") -> str:
        import litellm
        from app.core.config import settings
        from app.agents.engine import _get_gemini_key
        key = self._api_key or _get_gemini_key()
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_key=key,
        )
        return response.choices[0].message.content or ""


class KeyValueStore:
    """Persistent key-value store for automation state between runs."""
    def __init__(self, automation_id: str):
        self._automation_id = automation_id

    async def get(self, key: str, default: Any = None) -> Any:
        from app.core.redis import redis_client
        raw = await redis_client.get(f"automation:{self._automation_id}:store:{key}")
        if raw is None:
            return default
        return json.loads(raw if isinstance(raw, str) else raw.decode())

    async def set(self, key: str, value: Any) -> None:
        from app.core.redis import redis_client
        await redis_client.set(
            f"automation:{self._automation_id}:store:{key}",
            json.dumps(value),
        )


class ToolProxy:
    """Exposes all connected tools as async methods."""
    def __init__(self, user_id: str):
        self._user_id = user_id
        self._tools = None

    async def _ensure_tools(self):
        if self._tools is None:
            from app.integrations.registry import integration_registry
            self._tools = await integration_registry.get_tools_for_user(self._user_id)

    def __getattr__(self, name: str):
        async def call(**kwargs):
            await self._ensure_tools()
            if name not in self._tools:
                raise AttributeError(f"Tool '{name}' not available. Is the integration connected?")
            return await self._tools[name]["fn"](**kwargs)
        return call


class AutomationContext:
    """Injected as `ctx` into automation scripts."""
    def __init__(self, user_id: str, automation_id: str, api_key: str | None = None):
        self.tools = ToolProxy(user_id)
        self.ai = AIProxy(api_key)
        self.now = datetime.now(SP_TZ)
        self.store = KeyValueStore(automation_id)
        self.user_id = user_id
        self._logs: list[str] = []
        self._output: str = ""

    def log(self, msg: str):
        logger.info(f"[automation:{self.user_id}] {msg}")
        self._logs.append(msg)

    def set_output(self, output: str):
        self._output = output
