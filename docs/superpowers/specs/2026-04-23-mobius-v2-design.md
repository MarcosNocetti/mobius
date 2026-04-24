# Mobius v2 — Plugin Architecture + Automation Engine

## Overview

Refactor Mobius from flat integration modules to a **plugin-based architecture** with auto-discovered tools, and build a **conversational automation engine** that generates Python scripts executed by Celery workers.

**Goals:**
1. Add 7 new integrations (GitHub, Slack, Teams, Jira, Azure DevOps, n8n, Claude Platform) with SSO login
2. Eliminate OAuth boilerplate duplication via `IntegrationBase` ABC
3. Auto-discover tools via `@tool_action` decorator — zero manual registry edits
4. Build automation engine: user describes intent → AI refines → generates script → Celery executes
5. Adjust Flutter UI to support dynamic integrations and richer automation management

**Non-goals:**
- No visual drag-and-drop automation builder (future)
- No MCP protocol (overengineered for current scale)
- No new Flutter screens — only adjustments to existing ones

---

## 1. Plugin Architecture (IntegrationBase)

### 1.1 Base Class

```python
# app/integrations/base.py

class IntegrationBase(ABC):
    name: str              # "github"
    display_name: str      # "GitHub"
    icon: str              # "github" (for Flutter icon mapping)
    auth_type: str         # "oauth2" | "api_key" | "webhook"
    scopes: list[str]      # OAuth scopes or empty
    base_api_url: str      # "https://api.github.com"

    @abstractmethod
    async def get_authorize_url(self, user_id: str, base_url: str) -> str: ...

    @abstractmethod
    async def handle_callback(self, code: str, state: str) -> dict: ...

    async def refresh_token(self, user_id: str) -> str: ...

    async def is_connected(self, user_id: str) -> bool:
        raw = await redis_client.get(f"oauth:{self.name}:{user_id}")
        return bool(raw)

    async def get_access_token(self, user_id: str) -> str:
        # With auto-refresh on 401 (same pattern as current Google)
        ...

    async def api_request(self, method: str, url: str, user_id: str, **kwargs) -> Response:
        # Auto-refresh wrapper (like current _google_request)
        ...

    def get_tools(self) -> list[ToolDefinition]:
        # Auto-discovered from @tool_action in this integration's tools.py
        ...
```

### 1.2 Concrete Implementations

For OAuth integrations (GitHub, Slack, Teams, Jira, Azure DevOps):
```python
# app/integrations/github/__init__.py

class GitHubIntegration(IntegrationBase):
    name = "github"
    display_name = "GitHub"
    auth_type = "oauth2"
    scopes = ["repo", "read:user", "read:org"]
    base_api_url = "https://api.github.com"

    async def get_authorize_url(self, user_id, base_url):
        return f"https://github.com/login/oauth/authorize?client_id={...}&scope={...}&state={user_id}"

    async def handle_callback(self, code, state):
        # Exchange code for token, store in Redis
        ...
```

For API Key integrations (n8n, Claude Platform):
```python
# app/integrations/n8n/__init__.py

class N8nIntegration(IntegrationBase):
    name = "n8n"
    display_name = "n8n"
    auth_type = "api_key"

    async def get_authorize_url(self, user_id, base_url):
        return None  # No OAuth — configured via Settings

    async def is_connected(self, user_id):
        # Check if API key exists in user's stored keys
        ...
```

### 1.3 Integration Registry

```python
# app/integrations/registry.py

_integrations: dict[str, IntegrationBase] = {}

def discover_integrations():
    """Scan app/integrations/*/  and instantiate IntegrationBase subclasses."""
    ...

def get_integration(name: str) -> IntegrationBase: ...
def get_all_integrations() -> list[IntegrationBase]: ...
```

### 1.4 Unified API Endpoints

```python
# app/api/connect.py — replaces current setup.py

@router.get("/connect/{integration}")
async def connect(integration: str, user_id: str = None): ...

@router.get("/connect/{integration}/callback")
async def callback(integration: str, code: str, state: str): ...

@router.get("/connect/status")
async def all_status(user_id: str): ...
# Returns: {"github": true, "slack": false, "google": true, ...}
```

### 1.5 Settings for env vars

Each integration reads its credentials from env vars following a convention:
```
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
JIRA_CLIENT_ID=...
...
N8N_BASE_URL=...
CLAUDE_API_KEY=...
```

All stored as GitHub Secrets + local `.env`.

---

## 2. Tool Auto-Discovery (@tool_action)

### 2.1 Decorator

```python
# app/agents/tools/decorator.py

def tool_action(name: str, description: str, params: dict, integration: str = None):
    """Register a function as an AI-callable tool."""
    def wrapper(fn):
        fn._tool_meta = ToolMeta(name, description, params, integration or _infer_integration(fn))
        return fn
    return wrapper
```

### 2.2 Tool Definition in Integration Modules

```python
# app/integrations/github/tools.py

@tool_action(
    name="create_github_issue",
    description="Create an issue in a GitHub repository",
    params={
        "repo": {"type": "string", "description": "Repository in owner/repo format"},
        "title": {"type": "string", "description": "Issue title"},
        "body": {"type": "string", "description": "Issue description (markdown)"},
        "labels": {"type": "array", "items": {"type": "string"}, "description": "Labels (optional)"},
    },
)
async def create_issue(user_id: str, repo: str, title: str, body: str, labels: list = None) -> str:
    integration = get_integration("github")
    resp = await integration.api_request("post", f"/repos/{repo}/issues", user_id, json={
        "title": title, "body": body, "labels": labels or [],
    })
    data = resp.json()
    return f"Issue #{data['number']} created: {data['html_url']}"
```

### 2.3 Auto-Discovery Registry

```python
# app/agents/tools/registry.py (rewritten)

_discovered_tools: dict[str, list[ToolDefinition]] = {}

def discover_tools():
    """Scan all app/integrations/*/tools.py for @tool_action decorated functions."""
    for module_path in glob("app/integrations/*/tools.py"):
        module = importlib.import_module(module_path)
        for obj in vars(module).values():
            if hasattr(obj, '_tool_meta'):
                meta = obj._tool_meta
                _discovered_tools.setdefault(meta.integration, []).append(
                    ToolDefinition(name=meta.name, fn=obj, schema=meta.to_openai_schema())
                )

def get_tools_for_user(user_id: str, connected_integrations: list[str]) -> dict:
    """Return only tools whose integration is connected for this user."""
    tools = {}
    for integration_name, tool_list in _discovered_tools.items():
        if integration_name in connected_integrations:
            for tool in tool_list:
                tools[tool.name] = {"fn": tool.bind(user_id), "schema": tool.schema}
    return tools
```

---

## 3. The 7 New Integrations

### 3.1 GitHub (OAuth App)

Tools:
- `create_github_issue(repo, title, body, labels)`
- `list_github_issues(repo, state, labels)`
- `create_pull_request(repo, title, body, head, base)`
- `list_pull_requests(repo, state)`
- `merge_pull_request(repo, pr_number)`
- `get_repo_info(repo)`
- `search_code(query)`
- `list_repos()`

OAuth: GitHub OAuth App → `https://github.com/login/oauth/authorize`

### 3.2 Slack (OAuth v2)

Tools:
- `send_slack_message(channel, text)`
- `read_slack_channel(channel, limit)`
- `list_slack_channels()`
- `search_slack_messages(query)`
- `set_slack_status(text, emoji)`

OAuth: Slack OAuth v2 → `https://slack.com/oauth/v2/authorize`

### 3.3 Microsoft Teams (Azure AD OAuth)

Tools:
- `send_teams_message(team, channel, text)`
- `read_teams_channel(team, channel, limit)`
- `list_teams()`
- `create_teams_meeting(subject, start_dt, end_dt, attendees)`

OAuth: Azure AD → `https://login.microsoftonline.com/common/oauth2/v2.0/authorize`

### 3.4 Jira (OAuth 2.0 3LO)

Tools:
- `create_jira_issue(project, summary, description, issue_type)`
- `update_jira_issue(issue_key, fields)`
- `transition_jira_issue(issue_key, transition)`
- `search_jira(jql)`
- `list_jira_sprints(board_id)`
- `get_jira_board(board_id)`

OAuth: Atlassian OAuth 2.0 (3LO) → `https://auth.atlassian.com/authorize`

### 3.5 Azure DevOps (Azure AD OAuth)

Tools:
- `create_work_item(project, type, title, description)`
- `update_work_item(id, fields)`
- `list_work_items(project, query)`
- `list_pipelines(project)`
- `trigger_pipeline(project, pipeline_id)`
- `create_devops_pr(project, repo, title, source, target)`

OAuth: Azure AD (same as Teams, different scopes)

### 3.6 n8n (API Key)

Tools:
- `list_n8n_workflows()`
- `execute_n8n_workflow(workflow_id, data)`
- `get_n8n_execution(execution_id)`
- `create_n8n_webhook(workflow_id, path)`

Auth: API Key stored in user settings. `N8N_BASE_URL` env var for server address.

### 3.7 Claude Platform (API Key)

Tools:
- `create_claude_batch(prompts, model)`
- `get_claude_batch_status(batch_id)`
- `list_claude_models()`

Auth: API Key stored in user settings. Used for batch/scheduled processing, not as chat model.

---

## 4. Automation Engine

### 4.1 Data Model

```python
class Automation(Base):
    __tablename__ = "automations"
    id: Mapped[str]                    # UUID
    user_id: Mapped[str]               # FK to User
    name: Mapped[str]                  # "Daily email summary"
    description: Mapped[str]           # User-friendly description
    trigger_type: Mapped[str]          # "cron" | "webhook" | "manual"
    trigger_config: Mapped[dict]       # {"cron": "0 9 * * *"}
    script: Mapped[str]                # Python source code
    status: Mapped[str]                # "draft" | "active" | "paused" | "error"
    last_run: Mapped[datetime | None]
    last_result: Mapped[str | None]    # Last execution result/output
    last_error: Mapped[str | None]     # Last error traceback
    run_count: Mapped[int]             # Total executions
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### 4.2 AutomationContext (Runtime)

```python
class AutomationContext:
    """Injected as `ctx` into automation scripts."""
    tools: ToolProxy          # ctx.tools.read_gmail(query="...")
    ai: AIProxy               # ctx.ai.ask("summarize this: ...")
    now: datetime             # Current datetime (timezone-aware)
    store: KeyValueStore      # ctx.store.get("last_count"), ctx.store.set("last_count", 5)
    log: Callable             # ctx.log("Processing 5 emails...")
    user_id: str              # For internal use
```

`ToolProxy` dynamically exposes all connected tools as async methods.
`AIProxy.ask()` calls `litellm.acompletion` with key rotation.
`KeyValueStore` persists to Redis with key `automation:{id}:store:{key}`.

### 4.3 Script Execution (Celery Worker)

```python
# app/workers/automation_worker.py

@celery_app.task(bind=True, max_retries=2, time_limit=300)
def execute_automation(self, automation_id: str):
    """Load script from DB, create context, execute in sandbox."""
    automation = db.get(automation_id)
    ctx = AutomationContext(
        user_id=automation.user_id,
        tools=ToolProxy(automation.user_id),
        ai=AIProxy(),
        store=KeyValueStore(automation.id),
    )
    try:
        exec(automation.script, {"ctx": ctx, "__builtins__": SAFE_BUILTINS})
        automation.last_result = ctx._output
        automation.status = "active"
    except Exception as e:
        automation.last_error = traceback.format_exc()
        automation.status = "error"
    automation.last_run = datetime.utcnow()
    automation.run_count += 1
    db.save(automation)
```

### 4.4 Conversational Creation Flow

The chat system prompt includes instructions to detect automation requests:

```
When the user wants to create an automation:
1. Identify the trigger (when should it run?)
2. Identify the actions (what should it do?)
3. Generate a Python script using ctx.tools.* and ctx.ai.*
4. Show the user a preview: name, trigger, description, and the script
5. Ask for confirmation
6. On approval, call create_automation tool to save it
```

New tools for automation management:
- `create_automation(name, description, trigger_type, trigger_config, script)` — saves to DB + registers in Celery Beat
- `list_automations()` — returns user's automations with status
- `edit_automation(id, script)` — updates an existing automation's script
- `toggle_automation(id)` — pause/resume
- `run_automation_now(id)` — trigger immediate execution
- `delete_automation(id)`

### 4.5 Security

- Scripts execute with restricted globals: only `ctx` and safe builtins (no `import`, `open`, `eval`, `exec`)
- 5 minute timeout per execution
- No filesystem or network access outside `ctx.tools` and `ctx.ai`
- Errors captured and stored, don't crash the worker

---

## 5. Flutter UI Adjustments

### 5.1 Integrations Screen (existing — adjust)

**Current:** Hardcoded 5 integrations from `/integrations/status`
**New:** Dynamic list from `/connect/status` which returns all registered integrations:

```json
{
  "integrations": [
    {"name": "google", "display_name": "Google Workspace", "connected": true, "auth_type": "oauth2"},
    {"name": "github", "display_name": "GitHub", "connected": false, "auth_type": "oauth2"},
    {"name": "n8n", "display_name": "n8n", "connected": false, "auth_type": "api_key"},
    ...
  ]
}
```

- OAuth integrations: "Connect" button opens `/connect/{name}` in browser
- API Key integrations: inline text field + test button (like current Settings API keys)
- Connected integrations show green badge + "Disconnect" option

### 5.2 Automations Screen (existing — adjust)

**Current:** Simple list with prompt + cron. 
**New:**

- Each automation card shows: name, description, status badge (active/paused/error), last run time, next run time
- Status badge colors: green=active, yellow=paused, red=error
- Tap to expand: shows last result or error message
- Swipe to delete (already exists)
- Toggle switch for pause/resume (already exists, add status tracking)
- **New "Run Now" button**: triggers immediate execution via `POST /automations/{id}/run`
- FAB "+" opens bottom sheet (already exists, keep as is — the chat is the primary creation flow)

### 5.3 Chat Screen (no changes)

Tools appear/disappear automatically based on connected integrations. The system prompt instructs the AI to guide users through automation creation conversationally. No UI changes needed.

### 5.4 Settings Screen (minimal changes)

- API Key fields for n8n and Claude Platform (same pattern as Gemini key with test button)
- Remove Accessibility section (not relevant for v2 scope)

---

## 6. Infrastructure

### 6.1 Celery + Redis

```
[FastAPI Server] ──WebSocket/REST──> [Flutter App]
       │
       ├── Redis (tokens, locks, automation store)
       │
       └── Celery Worker(s)
            ├── Celery Beat (cron scheduler)
            └── Task: execute_automation
```

New dependencies: `celery[redis]`, `celery-beat`
Replaces: APScheduler (removed from main.py lifespan)

### 6.2 Environment Variables (new)

```env
# GitHub
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Slack
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=

# Microsoft (Teams + Azure DevOps share tenant)
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=common

# Jira
JIRA_CLIENT_ID=
JIRA_CLIENT_SECRET=

# n8n (per-user API key, no server-side credential needed)
# Claude Platform (per-user API key)
```

### 6.3 Directory Structure (final)

```
mobius-server/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── redis.py
│   │   ├── security.py
│   │   └── celery.py              # NEW — Celery app config
│   ├── api/
│   │   ├── router.py
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── connect.py             # NEW — replaces setup.py
│   │   └── automations.py         # UPDATED — richer CRUD + run-now
│   ├── agents/
│   │   ├── engine.py
│   │   └── tools/
│   │       ├── decorator.py       # NEW — @tool_action
│   │       └── registry.py        # REWRITTEN — auto-discovery
│   ├── integrations/
│   │   ├── base.py                # NEW — IntegrationBase ABC
│   │   ├── registry.py            # NEW — integration auto-discovery
│   │   ├── google/
│   │   │   ├── __init__.py        # GoogleIntegration(IntegrationBase)
│   │   │   └── tools.py           # @tool_action functions
│   │   ├── github/                # NEW
│   │   ├── slack/                 # NEW
│   │   ├── teams/                 # NEW
│   │   ├── jira/                  # NEW
│   │   ├── azure_devops/          # NEW
│   │   ├── n8n/                   # NEW
│   │   ├── claude_platform/       # NEW
│   │   ├── twitter/               # MIGRATED to plugin pattern
│   │   ├── notion/                # MIGRATED to plugin pattern
│   │   ├── instagram/             # MIGRATED to plugin pattern
│   │   └── linkedin/              # MIGRATED to plugin pattern
│   ├── workers/
│   │   ├── __init__.py            # NEW
│   │   ├── celery_app.py          # NEW — Celery instance
│   │   └── automation_worker.py   # NEW — script executor
│   ├── automation/
│   │   ├── context.py             # NEW — AutomationContext
│   │   ├── sandbox.py             # NEW — restricted exec
│   │   └── store.py               # NEW — KeyValueStore
│   └── models/
│       ├── user.py
│       ├── conversation.py
│       └── automation.py          # UPDATED — richer schema
├── tests/
│   ├── test_integration_base.py   # NEW
│   ├── test_tool_discovery.py     # NEW
│   ├── test_automation_engine.py  # NEW
│   ├── test_celery_worker.py      # NEW
│   ├── test_integrations/
│   │   ├── test_github.py         # NEW
│   │   ├── test_slack.py          # NEW
│   │   ├── test_jira.py           # NEW
│   │   ├── test_teams.py          # NEW
│   │   ├── test_azure_devops.py   # NEW
│   │   ├── test_n8n.py            # NEW
│   │   └── test_claude_platform.py# NEW
│   └── ... (existing tests)
├── docker-compose.yml             # UPDATED — add celery worker
├── requirements.txt               # UPDATED — add celery
└── .env.example                   # UPDATED — new integration vars
```

---

## 7. Testing Strategy

### 7.1 Unit Tests (~60)

Per integration (~5 each × 12):
- OAuth flow (authorize URL generation, callback handling, token refresh)
- Each tool function (mock HTTP, verify params/response)

### 7.2 Architecture Tests (~10)

- IntegrationBase contract enforcement
- Tool auto-discovery (decorator → registry)
- Integration registry (discover all modules)
- Connected-tools filtering

### 7.3 Automation Engine Tests (~15)

- AutomationContext (tools proxy, ai proxy, store)
- Script sandbox (restricted builtins, no imports)
- Celery task execution (success, timeout, error capture)
- Cron registration/deregistration
- Conversational creation flow (chat → script → save)

### 7.4 API Tests (~5)

- `GET /connect/{integration}` redirect
- `GET /connect/{integration}/callback` token storage
- `GET /connect/status` all integrations
- `POST /automations/{id}/run` immediate execution
- Automation CRUD with new fields

### 7.5 Total: ~90 new tests

All tests use mocked HTTP clients (no real API keys needed).

---

## 8. Migration from Current Architecture

### What changes:
- `app/integrations/google.py` → `app/integrations/google/__init__.py` + `tools.py`
- Same for twitter, notion, instagram, linkedin
- `app/agents/tools/registry.py` → rewritten with auto-discovery
- `app/api/setup.py` → replaced by `app/api/connect.py`
- APScheduler → Celery Beat
- `app/models/automation.py` → expanded schema

### What stays:
- `app/agents/engine.py` — mostly unchanged, just uses new registry API
- `app/api/chat.py` — mostly unchanged, gets tools from new registry
- `app/api/auth.py` — unchanged
- `app/core/*` — unchanged (add celery.py)
- All Flutter screens — adjusted, not rewritten
- JWT auth, WebSocket streaming, LiteLLM — all unchanged
