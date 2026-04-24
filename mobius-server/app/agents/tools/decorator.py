from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolMeta:
    name: str
    description: str
    integration: str
    params: dict[str, dict]

    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.params,
                    "required": [k for k in self.params],
                },
            },
        }

    def bind(self, user_id: str, fn: Callable) -> Callable:
        async def bound(**kwargs):
            return await fn(user_id, **kwargs)
        return bound


def tool_action(
    name: str,
    description: str,
    integration: str,
    params: dict[str, dict],
) -> Callable:
    def wrapper(fn: Callable) -> Callable:
        fn._tool_meta = ToolMeta(
            name=name,
            description=description,
            integration=integration,
            params=params,
        )
        return fn
    return wrapper
