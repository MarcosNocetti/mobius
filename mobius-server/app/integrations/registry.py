"""
Integration Registry — auto-discovers IntegrationBase subclasses
and @tool_action decorated functions from app/integrations/*/
"""
import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any, Callable

from app.integrations.base import IntegrationBase

logger = logging.getLogger("mobius.registry")


class IntegrationRegistry:
    def __init__(self):
        self._integrations: dict[str, IntegrationBase] = {}
        self._tools: dict[str, dict] = {}  # name -> {"fn": fn, "meta": ToolMeta}
        self._discovered = False

    def _discover(self):
        if self._discovered:
            return
        self._discovered = True

        integrations_dir = Path(__file__).parent
        for entry in sorted(integrations_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith(("_", ".")):
                continue
            # Try to import the package __init__
            module_name = f"app.integrations.{entry.name}"
            try:
                mod = importlib.import_module(module_name)
            except Exception as exc:
                logger.warning(f"Skipping integration {entry.name}: {exc}")
                continue

            # Find IntegrationBase subclass in the module
            for _attr_name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, IntegrationBase) and obj is not IntegrationBase:
                    instance = obj()
                    self._integrations[instance.name] = instance
                    break

            # Try to import tools.py
            tools_module_name = f"{module_name}.tools"
            try:
                tools_mod = importlib.import_module(tools_module_name)
            except Exception:
                # No tools module, or it failed — that's OK
                continue

            for _attr_name, fn in inspect.getmembers(tools_mod, inspect.isfunction):
                meta = getattr(fn, "_tool_meta", None)
                if meta is not None:
                    self._tools[meta.name] = {"fn": fn, "meta": meta}

        # Also discover system tools (automation management)
        try:
            import app.automation.tools as automation_tools
            for attr_name in dir(automation_tools):
                attr = getattr(automation_tools, attr_name)
                if callable(attr) and hasattr(attr, "_tool_meta"):
                    meta = attr._tool_meta
                    self._tools[meta.name] = {"fn": attr, "meta": meta}
                    logger.info(f"[registry] discovered system tool: {meta.name}")
        except Exception as e:
            logger.warning(f"[registry] failed to load automation tools: {e}")

    def get(self, name: str) -> IntegrationBase:
        self._discover()
        integration = self._integrations.get(name)
        if not integration:
            raise KeyError(f"Integration '{name}' not found")
        return integration

    def get_all(self) -> dict[str, IntegrationBase]:
        self._discover()
        return dict(self._integrations)

    async def get_all_status(self, user_id: str) -> list[dict]:
        self._discover()
        statuses = []
        for integration in self._integrations.values():
            statuses.append(await integration.to_status_dict(user_id))
        return statuses

    async def get_tools_for_user(self, user_id: str) -> dict[str, dict[str, Any]]:
        """
        Return tools only from connected integrations, bound to user_id.
        Format: {tool_name: {"fn": bound_callable, "schema": openai_schema_dict}}
        """
        self._discover()
        result: dict[str, dict[str, Any]] = {}

        for tool_name, entry in self._tools.items():
            meta = entry["meta"]
            fn = entry["fn"]
            integration_name = meta.integration

            # System tools are always available (no integration connection needed)
            if integration_name == "_system":
                bound_fn = meta.bind(user_id, fn)
                result[tool_name] = {
                    "fn": bound_fn,
                    "schema": meta.to_schema(),
                }
                continue

            integration = self._integrations.get(integration_name)
            if not integration:
                continue

            if not await integration.is_connected(user_id):
                continue

            bound_fn = meta.bind(user_id, fn)
            result[tool_name] = {
                "fn": bound_fn,
                "schema": meta.to_schema(),
            }

        return result


integration_registry = IntegrationRegistry()
