# Mobius v2 Plan 1: Plugin Architecture + Tool Auto-Discovery

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor Mobius from flat integration modules to a plugin-based architecture with `IntegrationBase` ABC, `@tool_action` decorator, and auto-discovered tool registry. Migrate all existing integrations (Google, Twitter, Notion, Instagram, LinkedIn) to the new pattern.

**Architecture:** Each integration becomes a folder with `__init__.py` (IntegrationBase subclass) and `tools.py` (@tool_action decorated functions). A central registry auto-discovers all integrations and tools at startup. The chat handler uses the registry to get tools filtered by connected integrations.

**Tech Stack:** Python 3.12, FastAPI, Redis (token storage), httpx (API calls), pytest

---

## Directory Structure

```
mobius-server/
├── app/
│   ├── integrations/
│   │   ├── base.py                    # NEW — IntegrationBase ABC
│   │   ├── registry.py                # NEW — Integration auto-discovery
│   │   ├── google/
│   │   │   ├── __init__.py            # MIGRATED — GoogleIntegration(IntegrationBase)
│   │   │   └── tools.py              # MIGRATED — @tool_action functions
│   │   ├── twitter/
│   │   │   ├── __init__.py            # MIGRATED
│   │   │   └── tools.py
│   │   ├── notion/
│   │   │   ├── __init__.py            # MIGRATED
│   │   │   └── tools.py
│   │   ├── instagram/
│   │   │   ├── __init__.py            # MIGRATED
│   │   │   └── tools.py
│   │   └── linkedin/
│   │       ├── __init__.py            # MIGRATED
│   │       └── tools.py
│   ├── agents/
│   │   └── tools/
│   │       ├── decorator.py           # NEW — @tool_action
│   │       └── registry.py            # REWRITTEN — auto-discovery
│   ├── api/
│   │   ├── connect.py                 # NEW — replaces setup.py
│   │   └── chat.py                    # UPDATED — uses new registry
│   └── ...
├── tests/
│   ├── test_integration_base.py       # NEW
│   ├── test_tool_discovery.py         # NEW
│   ├── test_connect_api.py            # NEW
│   └── ...
```

---

## Task 1: @tool_action Decorator

**Goal:** Create the decorator that marks async functions as AI-callable tools with JSON schema metadata.

**Files:**
- Create: `app/agents/tools/decorator.py`
- Create: `tests/test_tool_discovery.py`

### Step 1.1 — Write failing test

- [ ] Create `tests/test_tool_discovery.py`:

```python
import pytest
from app.agents.tools.decorator import tool_action, get_discovered_tools


def test_tool_action_registers_metadata():
    """Decorated function should have _tool_meta attribute."""

    @tool_action(
        name="test_tool",
        description="A test tool",
        integration="test",
        params={
            "arg1": {"type": "string", "description": "First arg"},
        },
    )
    async def my_tool(user_id: str, arg1: str) -> str:
        return f"result: {arg1}"

    assert hasattr(my_tool, "_tool_meta")
    assert my_tool._tool_meta.name == "test_tool"
    assert my_tool._tool_meta.description == "A test tool"
    assert my_tool._tool_meta.integration == "test"


def test_tool_meta_generates_openai_schema():
    """_tool_meta.to_schema() should produce valid OpenAI tool schema."""

    @tool_action(
        name="create_thing",
        description="Creates a thing",
        integration="test",
        params={
            "title": {"type": "string", "description": "Thing title"},
            "count": {"type": "integer", "description": "How many"},
        },
    )
    async def create_thing(user_id: str, title: str, count: int) -> str:
        return "done"

    schema = create_thing._tool_meta.to_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "create_thing"
    assert "title" in schema["function"]["parameters"]["properties"]
    assert "count" in schema["function"]["parameters"]["properties"]
    # user_id should NOT be in the schema (injected by engine)
    assert "user_id" not in schema["function"]["parameters"]["properties"]


def test_tool_meta_bind_injects_user_id():
    """bind(user_id) should return a callable with user_id pre-filled."""

    @tool_action(
        name="bound_tool",
        description="Test binding",
        integration="test",
        params={"msg": {"type": "string", "description": "Message"}},
    )
    async def send(user_id: str, msg: str) -> str:
        return f"{user_id}:{msg}"

    bound = send._tool_meta.bind("user-123", send)
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(bound(msg="hello"))
    assert result == "user-123:hello"
```

- [ ] Run test to verify it fails:

```bash
cd mobius-server && python3 -m pytest tests/test_tool_discovery.py -v
# Expected: ModuleNotFoundError: No module named 'app.agents.tools.decorator'
```

### Step 1.2 — Implement decorator

- [ ] Create `app/agents/tools/decorator.py`:

```python
"""
@tool_action decorator — marks async functions as AI-callable tools.
The decorator attaches a ToolMeta object with name, description, params,
and methods to generate OpenAI-compatible schemas and bind user_id.
"""
from dataclasses import dataclass, field
from typing import Any, Callable
from functools import partial


@dataclass
class ToolMeta:
    name: str
    description: str
    integration: str
    params: dict[str, dict]

    def to_schema(self) -> dict:
        """Generate OpenAI function-calling tool schema."""
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
        """Return a new callable with user_id pre-filled as first arg."""
        async def bound(**kwargs):
            return await fn(user_id, **kwargs)
        return bound


def tool_action(
    name: str,
    description: str,
    integration: str,
    params: dict[str, dict],
) -> Callable:
    """Decorator that attaches ToolMeta to an async function."""
    def wrapper(fn: Callable) -> Callable:
        fn._tool_meta = ToolMeta(
            name=name,
            description=description,
            integration=integration,
            params=params,
        )
        return fn
    return wrapper
```

- [ ] Run tests:

```bash
cd mobius-server && python3 -m pytest tests/test_tool_discovery.py -v
# Expected: 3 passed
```

- [ ] Commit:

```bash
git add app/agents/tools/decorator.py tests/test_tool_discovery.py
git commit -m "feat: @tool_action decorator with ToolMeta schema generation and user_id binding"
```

---

## Task 2: IntegrationBase ABC

**Goal:** Abstract base class for all integrations with OAuth flow, token management, and API request helpers.

**Files:**
- Create: `app/integrations/base.py`
- Create: `tests/test_integration_base.py`

### Step 2.1 — Write failing test

- [ ] Create `tests/test_integration_base.py`:

```python
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.integrations.base import IntegrationBase


class FakeIntegration(IntegrationBase):
    name = "fake"
    display_name = "Fake Service"
    auth_type = "oauth2"
    scopes = ["read", "write"]
    base_api_url = "https://api.fake.com"
    auth_url = "https://fake.com/oauth/authorize"
    token_url = "https://fake.com/oauth/token"

    def _get_client_id(self):
        return "fake-client-id"

    def _get_client_secret(self):
        return "fake-client-secret"


@pytest.fixture
def integration():
    return FakeIntegration()


async def test_get_authorize_url(integration):
    url = integration.get_authorize_url("user-1", "https://myapp.com")
    assert "fake-client-id" in url
    assert "user-1" in url
    assert "https://myapp.com" in url


async def test_is_connected_false_when_no_token(integration):
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        result = await integration.is_connected("user-1")
        assert result is False


async def test_is_connected_true_when_token_exists(integration):
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value=json.dumps({"access_token": "tok"}).encode())
        result = await integration.is_connected("user-1")
        assert result is True


async def test_handle_callback_stores_tokens(integration):
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "new-tok", "refresh_token": "ref-tok"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.integrations.base.redis_client") as mock_redis, \
         patch("app.integrations.base.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_redis.set = AsyncMock()

        tokens = await integration.handle_callback("auth-code", "user-1", "https://myapp.com")
        assert tokens["access_token"] == "new-tok"
        mock_redis.set.assert_called_once()


async def test_to_status_dict(integration):
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        status = await integration.to_status_dict("user-1")
        assert status["name"] == "fake"
        assert status["display_name"] == "Fake Service"
        assert status["connected"] is False
        assert status["auth_type"] == "oauth2"
```

- [ ] Run test to verify it fails:

```bash
cd mobius-server && python3 -m pytest tests/test_integration_base.py -v
# Expected: ModuleNotFoundError
```

### Step 2.2 — Implement IntegrationBase

- [ ] Create `app/integrations/base.py`:

```python
"""
IntegrationBase — abstract base class for all Mobius integrations.
Handles OAuth flow, token storage/refresh, and API request helpers.
"""
import json
import logging
from abc import ABC, abstractmethod
from urllib.parse import urlencode
import httpx
from app.core.redis import redis_client

logger = logging.getLogger("mobius.integration")


class IntegrationBase(ABC):
    name: str = ""
    display_name: str = ""
    auth_type: str = "oauth2"  # "oauth2" | "api_key"
    scopes: list[str] = []
    base_api_url: str = ""
    auth_url: str = ""
    token_url: str = ""

    @abstractmethod
    def _get_client_id(self) -> str: ...

    @abstractmethod
    def _get_client_secret(self) -> str: ...

    def _redis_key(self, user_id: str) -> str:
        return f"oauth:{self.name}:{user_id}"

    def get_authorize_url(self, user_id: str, base_url: str) -> str:
        """Build OAuth authorize redirect URL."""
        params = {
            "client_id": self._get_client_id(),
            "redirect_uri": f"{base_url}/connect/{self.name}/callback",
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": user_id,
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str, base_url: str) -> dict:
        """Exchange auth code for tokens and store in Redis."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data={
                "code": code,
                "client_id": self._get_client_id(),
                "client_secret": self._get_client_secret(),
                "redirect_uri": f"{base_url}/connect/{self.name}/callback",
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            tokens = resp.json()

        await redis_client.set(self._redis_key(state), json.dumps(tokens))
        logger.info(f"[{self.name}] tokens stored for user {state}")
        return tokens

    async def is_connected(self, user_id: str) -> bool:
        raw = await redis_client.get(self._redis_key(user_id))
        return bool(raw)

    async def get_access_token(self, user_id: str) -> tuple[str, dict]:
        """Get access token from Redis. Returns (token, full_tokens_dict)."""
        raw = await redis_client.get(self._redis_key(user_id))
        if not raw:
            raise ValueError(f"No {self.name} tokens for user {user_id}")
        tokens = json.loads(raw if isinstance(raw, str) else raw.decode())
        return tokens["access_token"], tokens

    async def refresh_token(self, user_id: str, tokens: dict) -> str:
        """Refresh the access token using refresh_token."""
        refresh = tokens.get("refresh_token")
        if not refresh:
            raise ValueError(f"No refresh token for {self.name} — user must re-authorize")
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data={
                "client_id": self._get_client_id(),
                "client_secret": self._get_client_secret(),
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            new_tokens = resp.json()

        tokens["access_token"] = new_tokens["access_token"]
        await redis_client.set(self._redis_key(user_id), json.dumps(tokens))
        logger.info(f"[{self.name}] refreshed token for user {user_id}")
        return new_tokens["access_token"]

    async def api_request(self, method: str, url: str, user_id: str, **kwargs) -> httpx.Response:
        """Make API request with auto-refresh on 401."""
        if not url.startswith("http"):
            url = f"{self.base_api_url}{url}"

        access_token, tokens = await self.get_access_token(user_id)
        async with httpx.AsyncClient() as client:
            resp = await getattr(client, method)(
                url, headers={"Authorization": f"Bearer {access_token}"}, **kwargs
            )
            if resp.status_code == 401:
                logger.info(f"[{self.name}] 401 for user {user_id}, refreshing...")
                new_token = await self.refresh_token(user_id, tokens)
                resp = await getattr(client, method)(
                    url, headers={"Authorization": f"Bearer {new_token}"}, **kwargs
                )
            resp.raise_for_status()
            return resp

    async def to_status_dict(self, user_id: str) -> dict:
        """Return status dict for the /connect/status endpoint."""
        connected = await self.is_connected(user_id)
        return {
            "name": self.name,
            "display_name": self.display_name,
            "connected": connected,
            "auth_type": self.auth_type,
        }
```

- [ ] Run tests:

```bash
cd mobius-server && python3 -m pytest tests/test_integration_base.py -v
# Expected: 5 passed
```

- [ ] Commit:

```bash
git add app/integrations/base.py tests/test_integration_base.py
git commit -m "feat: IntegrationBase ABC with OAuth flow, token refresh, and API request helpers"
```

---

## Task 3: Integration Registry (Auto-Discovery)

**Goal:** Scan `app/integrations/*/` at startup, instantiate all IntegrationBase subclasses, and discover all @tool_action functions.

**Files:**
- Create: `app/integrations/registry.py`
- Update: `tests/test_tool_discovery.py` (add registry tests)

### Step 3.1 — Write failing tests

- [ ] Add to `tests/test_tool_discovery.py`:

```python
from app.integrations.registry import IntegrationRegistry


def test_registry_discovers_integrations():
    """Registry should find all IntegrationBase subclasses in app/integrations/*/."""
    registry = IntegrationRegistry()
    registry.discover()
    # Should find at least google (migrated in Task 4)
    names = [i.name for i in registry.get_all()]
    assert len(names) > 0


def test_registry_get_by_name():
    """Registry should return integration by name."""
    registry = IntegrationRegistry()
    registry.discover()
    google = registry.get("google")
    assert google is not None
    assert google.display_name == "Google Workspace"


async def test_registry_get_tools_for_user():
    """Registry should return tools only for connected integrations."""
    registry = IntegrationRegistry()
    registry.discover()
    # With no integrations connected, should return empty
    from unittest.mock import AsyncMock, patch
    with patch("app.integrations.base.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        tools = await registry.get_tools_for_user("user-1")
        assert len(tools) == 0
```

- [ ] Run tests (should fail — registry module doesn't exist):

```bash
cd mobius-server && python3 -m pytest tests/test_tool_discovery.py::test_registry_discovers_integrations -v
```

### Step 3.2 — Implement registry

- [ ] Create `app/integrations/registry.py`:

```python
"""
Integration Registry — discovers all IntegrationBase subclasses and their tools.
"""
import importlib
import logging
import pkgutil
from pathlib import Path
from app.integrations.base import IntegrationBase

logger = logging.getLogger("mobius.registry")


class IntegrationRegistry:
    def __init__(self):
        self._integrations: dict[str, IntegrationBase] = {}
        self._tools: dict[str, list] = {}  # integration_name -> [tool_meta, ...]

    def discover(self):
        """Scan app/integrations/*/ for IntegrationBase subclasses and @tool_action functions."""
        integrations_dir = Path(__file__).parent
        for item in integrations_dir.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue
            # Try importing __init__.py for IntegrationBase subclass
            module_name = f"app.integrations.{item.name}"
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type)
                            and issubclass(attr, IntegrationBase)
                            and attr is not IntegrationBase
                            and hasattr(attr, 'name')
                            and attr.name):
                        instance = attr()
                        self._integrations[instance.name] = instance
                        logger.info(f"[registry] discovered integration: {instance.name}")
            except Exception as e:
                logger.warning(f"[registry] failed to load integration {item.name}: {e}")

            # Try importing tools.py for @tool_action functions
            tools_module_name = f"app.integrations.{item.name}.tools"
            try:
                tools_module = importlib.import_module(tools_module_name)
                tools = []
                for attr_name in dir(tools_module):
                    attr = getattr(tools_module, attr_name)
                    if callable(attr) and hasattr(attr, "_tool_meta"):
                        tools.append((attr, attr._tool_meta))
                        logger.info(f"[registry] discovered tool: {attr._tool_meta.name}")
                if tools:
                    integration_name = item.name
                    self._tools[integration_name] = tools
            except ModuleNotFoundError:
                pass  # No tools.py for this integration
            except Exception as e:
                logger.warning(f"[registry] failed to load tools for {item.name}: {e}")

    def get(self, name: str) -> IntegrationBase | None:
        return self._integrations.get(name)

    def get_all(self) -> list[IntegrationBase]:
        return list(self._integrations.values())

    async def get_all_status(self, user_id: str) -> list[dict]:
        """Return status dicts for all integrations."""
        return [await i.to_status_dict(user_id) for i in self._integrations.values()]

    async def get_tools_for_user(self, user_id: str) -> dict:
        """Return tools dict for connected integrations only."""
        tools = {}
        for integration_name, tool_list in self._tools.items():
            integration = self._integrations.get(integration_name)
            if integration and await integration.is_connected(user_id):
                for fn, meta in tool_list:
                    bound_fn = meta.bind(user_id, fn)
                    tools[meta.name] = {
                        "fn": bound_fn,
                        "schema": meta.to_schema(),
                    }
        return tools


# Global singleton — initialized on startup
integration_registry = IntegrationRegistry()
```

- [ ] Run tests (will pass once Google is migrated in Task 4):

```bash
cd mobius-server && python3 -m pytest tests/test_tool_discovery.py -v
```

- [ ] Commit:

```bash
git add app/integrations/registry.py tests/test_tool_discovery.py
git commit -m "feat: IntegrationRegistry with auto-discovery of integrations and tools"
```

---

## Task 4: Migrate Google Integration

**Goal:** Move Google from a flat file to the plugin pattern: `IntegrationBase` subclass + `@tool_action` tools.

**Files:**
- Create: `app/integrations/google/__init__.py`
- Create: `app/integrations/google/tools.py`
- Delete: `app/integrations/google.py` (old flat file)
- Update: `tests/test_integrations/test_google.py`

### Step 4.1 — Create Google integration class

- [ ] Create directory and `app/integrations/google/__init__.py`:

```python
from app.integrations.base import IntegrationBase
from app.core.config import settings


class GoogleIntegration(IntegrationBase):
    name = "google"
    display_name = "Google Workspace"
    auth_type = "oauth2"
    scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/tasks",
    ]
    base_api_url = ""  # Google uses full URLs per service
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"

    def _get_client_id(self) -> str:
        return settings.GOOGLE_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.GOOGLE_CLIENT_SECRET

    def get_authorize_url(self, user_id: str, base_url: str) -> str:
        """Override to add access_type=offline and prompt=consent."""
        url = super().get_authorize_url(user_id, base_url)
        return url + "&access_type=offline&prompt=consent"
```

### Step 4.2 — Create Google tools

- [ ] Create `app/integrations/google/tools.py`:

```python
import json
import base64
from email.mime.text import MIMEText
from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


async def _google_request(method: str, url: str, user_id: str, **kwargs):
    """Helper to make Google API requests via the integration base."""
    integration = integration_registry.get("google")
    return await integration.api_request(method, url, user_id, **kwargs)


@tool_action(
    name="create_calendar_event",
    description="Create an event on Google Calendar. Use ISO 8601 datetime (e.g. 2026-04-24T10:00:00-03:00).",
    integration="google",
    params={
        "title": {"type": "string", "description": "Event title"},
        "start_dt": {"type": "string", "description": "Start datetime ISO 8601"},
        "end_dt": {"type": "string", "description": "End datetime ISO 8601"},
    },
)
async def create_calendar_event(user_id: str, title: str, start_dt: str, end_dt: str) -> str:
    resp = await _google_request("post",
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        user_id, json={
            "summary": title,
            "start": {"dateTime": start_dt, "timeZone": "America/Sao_Paulo"},
            "end": {"dateTime": end_dt, "timeZone": "America/Sao_Paulo"},
        })
    data = resp.json()
    return f"Event created: {data.get('summary')} ({data.get('htmlLink')})"


@tool_action(
    name="list_calendar_events",
    description="List upcoming Google Calendar events in a time range. Use ISO 8601.",
    integration="google",
    params={
        "time_min": {"type": "string", "description": "Start of range ISO 8601"},
        "time_max": {"type": "string", "description": "End of range ISO 8601"},
    },
)
async def list_calendar_events(user_id: str, time_min: str, time_max: str) -> str:
    resp = await _google_request("get",
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        user_id, params={"timeMin": time_min, "timeMax": time_max, "maxResults": 10,
                         "singleEvents": "true", "orderBy": "startTime"})
    events = resp.json().get("items", [])
    lines = [f"- {e.get('summary', 'No title')} | {e.get('start', {}).get('dateTime', 'N/A')}" for e in events]
    return "\n".join(lines) if lines else "No events found"


@tool_action(
    name="send_gmail",
    description="Send an email via Gmail.",
    integration="google",
    params={
        "to": {"type": "string", "description": "Recipient email"},
        "subject": {"type": "string", "description": "Subject line"},
        "body": {"type": "string", "description": "Email body"},
    },
)
async def send_gmail(user_id: str, to: str, subject: str, body: str) -> str:
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    resp = await _google_request("post",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        user_id, json={"raw": raw})
    return f"Email sent to {to}: {resp.json().get('id')}"


@tool_action(
    name="read_gmail",
    description="Search and read Gmail messages. Use Gmail search syntax (e.g. 'is:unread', 'from:boss@co.com').",
    integration="google",
    params={
        "query": {"type": "string", "description": "Gmail search query (default: is:unread)"},
    },
)
async def read_gmail(user_id: str, query: str = "is:unread") -> str:
    resp = await _google_request("get",
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        user_id, params={"q": query, "maxResults": 5})
    messages = resp.json().get("messages", [])
    results = []
    for msg in messages[:5]:
        detail = await _google_request("get",
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
            user_id, params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]})
        headers = {h["name"]: h["value"] for h in detail.json().get("payload", {}).get("headers", [])}
        results.append(f"- From: {headers.get('From', '?')} | Subject: {headers.get('Subject', '?')} | {headers.get('Date', '?')}")
    return "\n".join(results) if results else "No messages found"


@tool_action(
    name="create_google_doc",
    description="Create a Google Doc with text content. Returns the document URL.",
    integration="google",
    params={
        "title": {"type": "string", "description": "Document title"},
        "content": {"type": "string", "description": "Document text content"},
    },
)
async def create_google_doc(user_id: str, title: str, content: str) -> str:
    resp = await _google_request("post", "https://docs.googleapis.com/v1/documents",
                                  user_id, json={"title": title})
    doc = resp.json()
    doc_id = doc["documentId"]
    if content:
        await _google_request("post", f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
                               user_id, json={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]})
    return f"Doc created: https://docs.google.com/document/d/{doc_id}"


@tool_action(
    name="create_spreadsheet",
    description="Create a Google Spreadsheet. Optionally provide initial data as rows.",
    integration="google",
    params={
        "title": {"type": "string", "description": "Spreadsheet title"},
        "data": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}, "description": "Data rows (optional)"},
    },
)
async def create_spreadsheet(user_id: str, title: str, data: list = None) -> str:
    resp = await _google_request("post", "https://sheets.googleapis.com/v4/spreadsheets",
                                  user_id, json={"properties": {"title": title}})
    sheet = resp.json()
    sheet_id = sheet["spreadsheetId"]
    if data:
        await _google_request("put",
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/A1",
            user_id, params={"valueInputOption": "RAW"}, json={"values": data})
    return f"Spreadsheet created: https://docs.google.com/spreadsheets/d/{sheet_id}"


@tool_action(
    name="list_drive_files",
    description="Search files in Google Drive by name.",
    integration="google",
    params={
        "query": {"type": "string", "description": "Search query (file name)"},
    },
)
async def list_drive_files(user_id: str, query: str = "") -> str:
    params = {"pageSize": 10, "fields": "files(id,name,mimeType,webViewLink)"}
    if query:
        params["q"] = f"name contains '{query}'"
    resp = await _google_request("get", "https://www.googleapis.com/drive/v3/files", user_id, params=params)
    files = resp.json().get("files", [])
    lines = [f"- {f['name']} ({f.get('mimeType', '?')}) {f.get('webViewLink', '')}" for f in files]
    return "\n".join(lines) if lines else "No files found"


@tool_action(
    name="create_task",
    description="Create a Google Task with title and optional notes/due date.",
    integration="google",
    params={
        "title": {"type": "string", "description": "Task title"},
        "notes": {"type": "string", "description": "Task notes (optional)"},
        "due": {"type": "string", "description": "Due date ISO 8601 (optional)"},
    },
)
async def create_task(user_id: str, title: str, notes: str = "", due: str = "") -> str:
    body = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due
    resp = await _google_request("post",
        "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks", user_id, json=body)
    return f"Task created: {resp.json().get('title')}"


@tool_action(
    name="list_tasks",
    description="List Google Tasks.",
    integration="google",
    params={},
)
async def list_tasks(user_id: str) -> str:
    resp = await _google_request("get",
        "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks", user_id, params={"maxResults": 10})
    tasks = resp.json().get("items", [])
    lines = [f"- [{t.get('status', '?')}] {t.get('title', '?')}" for t in tasks]
    return "\n".join(lines) if lines else "No tasks found"
```

### Step 4.3 — Update existing Google tests

- [ ] Update `tests/test_integrations/test_google.py` to import from new location:

```python
# Change imports from:
# from app.integrations.google import create_calendar_event, send_gmail
# To:
from app.integrations.google.tools import create_calendar_event, send_gmail
```

### Step 4.4 — Delete old flat file

- [ ] Remove `app/integrations/google.py` (replaced by `app/integrations/google/` folder)

```bash
rm app/integrations/google.py
```

### Step 4.5 — Run all tests

```bash
cd mobius-server && python3 -m pytest -v
# Expected: all tests pass
```

- [ ] Commit:

```bash
git add -A
git commit -m "refactor: migrate Google integration to plugin pattern with @tool_action"
```

---

## Task 5: Migrate Twitter, Notion, Instagram, LinkedIn

**Goal:** Move remaining 4 integrations to the plugin pattern. Same structure as Google.

**Files:**
- Create: `app/integrations/twitter/__init__.py`, `app/integrations/twitter/tools.py`
- Create: `app/integrations/notion/__init__.py`, `app/integrations/notion/tools.py`
- Create: `app/integrations/instagram/__init__.py`, `app/integrations/instagram/tools.py`
- Create: `app/integrations/linkedin/__init__.py`, `app/integrations/linkedin/tools.py`
- Delete: `app/integrations/twitter.py`, `app/integrations/notion.py`, `app/integrations/instagram.py`, `app/integrations/linkedin.py`

### Step 5.1 — Twitter

- [ ] Create `app/integrations/twitter/__init__.py`:

```python
import hashlib
import base64
import secrets
from urllib.parse import urlencode
import httpx
from app.integrations.base import IntegrationBase
from app.core.config import settings
from app.core.redis import redis_client
import json


class TwitterIntegration(IntegrationBase):
    name = "twitter"
    display_name = "Twitter / X"
    auth_type = "oauth2"
    scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]
    base_api_url = "https://api.twitter.com/2"
    auth_url = "https://twitter.com/i/oauth2/authorize"
    token_url = "https://api.twitter.com/2/oauth2/token"

    def _get_client_id(self) -> str:
        return settings.TWITTER_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.TWITTER_CLIENT_SECRET

    def get_authorize_url(self, user_id: str, base_url: str) -> str:
        """Override for PKCE flow."""
        verifier = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        # Store verifier in Redis for callback
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            redis_client.set(f"pkce:{self.name}:{user_id}", verifier, ex=600)
        )
        params = {
            "response_type": "code",
            "client_id": self._get_client_id(),
            "redirect_uri": f"{base_url}/connect/{self.name}/callback",
            "scope": " ".join(self.scopes),
            "state": user_id,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str, base_url: str) -> dict:
        """Override for PKCE token exchange."""
        verifier = await redis_client.get(f"pkce:{self.name}:{state}")
        if isinstance(verifier, bytes):
            verifier = verifier.decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": self._get_client_id(),
                "redirect_uri": f"{base_url}/connect/{self.name}/callback",
                "code_verifier": verifier,
            })
            resp.raise_for_status()
            tokens = resp.json()
        await redis_client.set(self._redis_key(state), json.dumps(tokens))
        return tokens
```

- [ ] Create `app/integrations/twitter/tools.py`:

```python
from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


@tool_action(
    name="post_tweet",
    description="Post a tweet on Twitter/X (max 280 chars).",
    integration="twitter",
    params={"text": {"type": "string", "description": "Tweet text"}},
)
async def post_tweet(user_id: str, text: str) -> str:
    integration = integration_registry.get("twitter")
    resp = await integration.api_request("post", "/tweets", user_id, json={"text": text})
    tweet_id = resp.json().get("data", {}).get("id", "?")
    return f"Tweet posted: https://twitter.com/i/web/status/{tweet_id}"
```

### Step 5.2 — Notion

- [ ] Create `app/integrations/notion/__init__.py`:

```python
from app.integrations.base import IntegrationBase
from app.core.config import settings


class NotionIntegration(IntegrationBase):
    name = "notion"
    display_name = "Notion"
    auth_type = "oauth2"
    scopes = []
    base_api_url = "https://api.notion.com/v1"
    auth_url = "https://api.notion.com/v1/oauth/authorize"
    token_url = "https://api.notion.com/v1/oauth/token"

    def _get_client_id(self) -> str:
        return settings.NOTION_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.NOTION_CLIENT_SECRET

    async def api_request(self, method, url, user_id, **kwargs):
        """Override to add Notion-Version header."""
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"]["Notion-Version"] = "2022-06-28"
        return await super().api_request(method, url, user_id, **kwargs)
```

- [ ] Create `app/integrations/notion/tools.py`:

```python
from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


@tool_action(
    name="create_notion_page",
    description="Create a page in Notion.",
    integration="notion",
    params={
        "title": {"type": "string", "description": "Page title"},
        "content": {"type": "string", "description": "Page content"},
    },
)
async def create_notion_page(user_id: str, title: str, content: str) -> str:
    integration = integration_registry.get("notion")
    resp = await integration.api_request("post", "/pages", user_id, json={
        "parent": {"database_id": ""},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": [{"object": "block", "type": "paragraph",
                       "paragraph": {"rich_text": [{"text": {"content": content}}]}}],
    })
    return f"Notion page created: {resp.json().get('url', '?')}"
```

### Step 5.3 — Instagram

- [ ] Create `app/integrations/instagram/__init__.py`:

```python
from app.integrations.base import IntegrationBase
from app.core.config import settings


class InstagramIntegration(IntegrationBase):
    name = "instagram"
    display_name = "Instagram"
    auth_type = "oauth2"
    scopes = ["instagram_basic", "instagram_content_publish"]
    base_api_url = "https://graph.facebook.com/v18.0"
    auth_url = "https://api.instagram.com/oauth/authorize"
    token_url = "https://api.instagram.com/oauth/access_token"

    def _get_client_id(self) -> str:
        return settings.INSTAGRAM_APP_ID

    def _get_client_secret(self) -> str:
        return settings.INSTAGRAM_APP_SECRET
```

- [ ] Create `app/integrations/instagram/tools.py`:

```python
from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


@tool_action(
    name="post_instagram",
    description="Post a photo to Instagram. Requires a public image URL.",
    integration="instagram",
    params={
        "image_url": {"type": "string", "description": "Public URL of image"},
        "caption": {"type": "string", "description": "Post caption"},
    },
)
async def post_instagram(user_id: str, image_url: str, caption: str) -> str:
    integration = integration_registry.get("instagram")
    # Step 1: Create media container
    resp1 = await integration.api_request("post", "/me/media", user_id, json={
        "image_url": image_url, "caption": caption,
    })
    container_id = resp1.json()["id"]
    # Step 2: Publish
    resp2 = await integration.api_request("post", "/me/media_publish", user_id, json={
        "creation_id": container_id,
    })
    return f"Instagram post published: {resp2.json().get('id', '?')}"
```

### Step 5.4 — LinkedIn

- [ ] Create `app/integrations/linkedin/__init__.py`:

```python
from app.integrations.base import IntegrationBase
from app.core.config import settings


class LinkedInIntegration(IntegrationBase):
    name = "linkedin"
    display_name = "LinkedIn"
    auth_type = "oauth2"
    scopes = ["openid", "profile", "w_member_social"]
    base_api_url = "https://api.linkedin.com/v2"
    auth_url = "https://www.linkedin.com/oauth/v2/authorization"
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"

    def _get_client_id(self) -> str:
        return settings.LINKEDIN_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.LINKEDIN_CLIENT_SECRET
```

- [ ] Create `app/integrations/linkedin/tools.py`:

```python
from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


@tool_action(
    name="post_linkedin",
    description="Post to LinkedIn.",
    integration="linkedin",
    params={"text": {"type": "string", "description": "Post text"}},
)
async def post_linkedin(user_id: str, text: str) -> str:
    integration = integration_registry.get("linkedin")
    # Get user URN
    me = await integration.api_request("get", "/userinfo", user_id)
    urn = f"urn:li:person:{me.json()['sub']}"
    resp = await integration.api_request("post", "/ugcPosts", user_id, json={
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "NONE",
        }},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    })
    return f"LinkedIn post published: {resp.json().get('id', '?')}"
```

### Step 5.5 — Delete old flat files

```bash
rm app/integrations/twitter.py app/integrations/notion.py app/integrations/instagram.py app/integrations/linkedin.py
```

### Step 5.6 — Run all tests

```bash
cd mobius-server && python3 -m pytest -v
# Expected: all tests pass (update imports in existing tests if needed)
```

- [ ] Commit:

```bash
git add -A
git commit -m "refactor: migrate Twitter, Notion, Instagram, LinkedIn to plugin pattern"
```

---

## Task 6: Unified /connect API + Update Chat Handler

**Goal:** Replace setup.py with generic /connect endpoints. Update chat.py to use the new registry.

**Files:**
- Create: `app/api/connect.py`
- Delete: `app/api/setup.py`
- Update: `app/api/chat.py`
- Update: `app/api/router.py`
- Update: `app/main.py` (initialize registry on startup)
- Create: `tests/test_connect_api.py`

### Step 6.1 — Write failing test

- [ ] Create `tests/test_connect_api.py`:

```python
import pytest


async def test_connect_status_returns_all_integrations(client):
    """GET /connect/status should list all integrations with connected status."""
    # Register a user first
    await client.post("/auth/register", json={"email": "connect@test.com", "password": "pass"})
    r = await client.post("/auth/token", json={"email": "connect@test.com", "password": "pass"})
    token = r.json()["access_token"]

    resp = await client.get(f"/connect/status?user_id=test-user")
    assert resp.status_code == 200
    data = resp.json()
    assert "integrations" in data
    # Should have at least google
    names = [i["name"] for i in data["integrations"]]
    assert "google" in names


async def test_connect_redirect_for_oauth(client):
    """GET /connect/google should redirect to Google OAuth."""
    resp = await client.get("/connect/google?user_id=test-user", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "accounts.google.com" in resp.headers.get("location", "")
```

### Step 6.2 — Implement connect.py

- [ ] Create `app/api/connect.py`:

```python
"""
Unified /connect endpoints for all integrations.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.integrations.registry import integration_registry

router = APIRouter(prefix="/connect", tags=["connect"])


@router.get("/status")
async def all_status(user_id: str | None = None):
    """Return connection status for all integrations."""
    if not user_id:
        # Return unconnected status for all
        return {"integrations": [
            {"name": i.name, "display_name": i.display_name, "connected": False, "auth_type": i.auth_type}
            for i in integration_registry.get_all()
        ]}
    statuses = await integration_registry.get_all_status(user_id)
    return {"integrations": statuses}


@router.get("/{integration_name}")
async def connect(request: Request, integration_name: str, user_id: str | None = None):
    """Start OAuth flow for an integration."""
    integration = integration_registry.get(integration_name)
    if not integration:
        return HTMLResponse(f"Integration '{integration_name}' not found", status_code=404)

    base_url = str(request.base_url).rstrip("/")

    # For API key integrations, no redirect needed
    if integration.auth_type == "api_key":
        return {"message": f"Configure {integration.display_name} API key in Settings"}

    # Resolve user_id if not provided
    if not user_id:
        from app.core.database import AsyncSessionLocal
        from app.models.user import User
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if not user:
                return HTMLResponse("No users registered. Sign up first.", status_code=400)
            user_id = str(user.id)

    url = integration.get_authorize_url(user_id, base_url)
    return RedirectResponse(url=url)


@router.get("/{integration_name}/callback")
async def callback(request: Request, integration_name: str, code: str, state: str):
    """Handle OAuth callback for any integration."""
    integration = integration_registry.get(integration_name)
    if not integration:
        return HTMLResponse(f"Integration '{integration_name}' not found", status_code=404)

    base_url = str(request.base_url).rstrip("/")
    await integration.handle_callback(code, state, base_url)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>body{{background:#0a0a1a;color:#e0e0e0;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}}
    .card{{text-align:center;background:#1a1a2e;padding:3rem;border-radius:16px;border:2px solid #4ade80}}
    h1{{color:#4ade80;font-size:2rem}}p{{color:#bbb;margin-top:1rem}}</style></head>
    <body><div class="card"><h1>✅ {integration.display_name} conectado!</h1><p>Pode fechar esta aba e voltar ao chat.</p></div></body></html>"""
    return HTMLResponse(content=html)
```

### Step 6.3 — Update chat.py to use registry

- [ ] Update `app/api/chat.py` — replace manual tool building with registry:

Replace the tool-building section (around lines 84-98) with:

```python
# Old:
# tool_registry = get_tools_for_user(user_id)
# if not google_connected:
#     tool_registry = {k: v for k, v in ...}

# New:
from app.integrations.registry import integration_registry
tool_registry = await integration_registry.get_tools_for_user(user_id)
```

Remove the `google_connected` check and the manual import of `get_tools_for_user`.

Update the Google status note to check via registry:

```python
google = integration_registry.get("google")
google_connected = await google.is_connected(user_id) if google else False
```

### Step 6.4 — Update router.py

- [ ] Update `app/api/router.py`:

```python
from app.api import auth, chat, automations, connect

router = APIRouter()
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(automations.router)
router.include_router(connect.router)
# Remove: integrations router (OAuth routes now handled by /connect)
# Remove: setup router
```

### Step 6.5 — Update main.py (initialize registry on startup)

- [ ] Add to `app/main.py` lifespan:

```python
from app.integrations.registry import integration_registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    integration_registry.discover()  # Auto-discover all integrations + tools
    # ... rest of lifespan
```

### Step 6.6 — Delete old files

```bash
rm app/api/setup.py
rm app/api/integrations.py
rm -rf app/agents/tools/productivity.py app/agents/tools/social.py app/agents/tools/utils.py
```

### Step 6.7 — Run all tests

```bash
cd mobius-server && python3 -m pytest -v
# Expected: all tests pass
```

- [ ] Commit:

```bash
git add -A
git commit -m "feat: unified /connect API, registry-based chat handler, remove old integration files"
```

---

## Task 7: Flutter UI — Dynamic Integrations Screen

**Goal:** Update the Integrations screen to load integrations dynamically from `/connect/status`.

**Files:**
- Update: `lib/features/integrations/integrations_provider.dart`
- Update: `lib/features/integrations/integrations_screen.dart`

### Step 7.1 — Update provider

- [ ] Rewrite `lib/features/integrations/integrations_provider.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../features/settings/settings_provider.dart';

class IntegrationStatus {
  final String name;
  final String displayName;
  final bool connected;
  final String authType;

  const IntegrationStatus({
    required this.name,
    required this.displayName,
    required this.connected,
    required this.authType,
  });

  factory IntegrationStatus.fromJson(Map<String, dynamic> json) => IntegrationStatus(
    name: json['name'] as String,
    displayName: json['display_name'] as String,
    connected: json['connected'] as bool,
    authType: json['auth_type'] as String,
  );
}

final integrationsProvider = FutureProvider<List<IntegrationStatus>>((ref) async {
  final client = ref.watch(backendClientProvider);
  final response = await client.get('/connect/status');
  final data = response.data as Map<String, dynamic>;
  final list = data['integrations'] as List<dynamic>;
  return list.map((e) => IntegrationStatus.fromJson(e as Map<String, dynamic>)).toList();
});
```

### Step 7.2 — Update screen

- [ ] Rewrite `lib/features/integrations/integrations_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../features/settings/settings_provider.dart';
import 'integrations_provider.dart';

class IntegrationsScreen extends ConsumerWidget {
  const IntegrationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final integrationsAsync = ref.watch(integrationsProvider);
    final settings = ref.watch(settingsNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Integrations')),
      body: integrationsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (integrations) => ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: integrations.length,
          separatorBuilder: (_, __) => const Divider(),
          itemBuilder: (context, index) {
            final i = integrations[index];
            return ListTile(
              title: Text(i.displayName),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Chip(
                    label: Text(
                      i.connected ? 'Connected' : 'Disconnected',
                      style: TextStyle(
                        color: i.connected ? Colors.green : Colors.grey,
                        fontSize: 12,
                      ),
                    ),
                    backgroundColor: i.connected
                        ? Colors.green.withOpacity(0.15)
                        : Colors.grey.withOpacity(0.15),
                  ),
                  const SizedBox(width: 8),
                  if (i.authType == 'oauth2')
                    TextButton(
                      onPressed: () async {
                        final url = Uri.parse(
                            '${settings.serverUrl}/connect/${i.name}');
                        if (await canLaunchUrl(url)) {
                          await launchUrl(url, mode: LaunchMode.externalApplication);
                        }
                      },
                      child: Text(i.connected ? 'Reconnect' : 'Connect'),
                    ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}
```

### Step 7.3 — Run codegen and tests

```bash
cp -r mobius-app/. /mnt/c/Users/Arklok/AppData/Local/Temp/mobius-build/
cmd.exe /c "cd /d C:\\Users\\Arklok\\AppData\\Local\\Temp\\mobius-build && flutter test"
```

- [ ] Commit:

```bash
git add lib/features/integrations/
git commit -m "feat: dynamic integrations screen loading from /connect/status"
```

---

## Task 8: Final — Run Full Test Suite + Push

**Goal:** Verify everything works together.

### Step 8.1 — Server tests

```bash
cd mobius-server && python3 -m pytest -v
# Expected: all tests pass (21 original + new tests)
```

### Step 8.2 — Flutter tests

```bash
# Copy to Windows and run
cp -r mobius-app/. /mnt/c/Users/Arklok/AppData/Local/Temp/mobius-build/
cmd.exe /c "cd /d C:\\Users\\Arklok\\AppData\\Local\\Temp\\mobius-build && dart pub run build_runner build --delete-conflicting-outputs && flutter test"
```

### Step 8.3 — Push

```bash
git push
```

---

## Test Summary

| Area | Tests | Description |
|------|-------|-------------|
| @tool_action decorator | 3 | metadata, schema gen, user_id binding |
| IntegrationBase | 5 | authorize URL, connected check, callback, token storage, status dict |
| IntegrationRegistry | 3 | discovery, get by name, tools for user |
| /connect API | 2 | status endpoint, OAuth redirect |
| Existing tests | 21 | Must continue passing |
| **Total** | **34** | |
