import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


def _jira():
    return integration_registry.get("jira")


@tool_action(
    name="create_jira_issue",
    description="Create a Jira issue.",
    integration="jira",
    params={
        "project": {"type": "string", "description": "Project key (e.g. PROJ)"},
        "summary": {"type": "string", "description": "Issue summary"},
        "description": {"type": "string", "description": "Issue description"},
        "issue_type": {"type": "string", "description": "Issue type (default: Task)"},
    },
)
async def create_jira_issue(user_id: str, project: str, summary: str, description: str, issue_type: str = "Task") -> str:
    resp = await _jira().api_request(
        "post", "/rest/api/3/issue", user_id,
        json={
            "fields": {
                "project": {"key": project},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
                },
                "issuetype": {"name": issue_type},
            }
        },
    )
    result = resp.json()
    return f"Issue created: {result.get('key')} — {summary}"


@tool_action(
    name="search_jira",
    description="Search Jira issues using JQL.",
    integration="jira",
    params={
        "jql": {"type": "string", "description": "JQL query"},
    },
)
async def search_jira(user_id: str, jql: str) -> str:
    resp = await _jira().api_request(
        "get", "/rest/api/3/search", user_id, params={"jql": jql, "maxResults": 10}
    )
    issues = [
        {"key": i["key"], "summary": i["fields"]["summary"], "status": i["fields"]["status"]["name"]}
        for i in resp.json().get("issues", [])
    ]
    return json.dumps(issues, ensure_ascii=False)


@tool_action(
    name="transition_jira_issue",
    description="Transition a Jira issue to a new status.",
    integration="jira",
    params={
        "issue_key": {"type": "string", "description": "Issue key (e.g. PROJ-123)"},
        "transition_name": {"type": "string", "description": "Transition name (e.g. Done)"},
    },
)
async def transition_jira_issue(user_id: str, issue_key: str, transition_name: str) -> str:
    # First, get available transitions
    resp = await _jira().api_request(
        "get", f"/rest/api/3/issue/{issue_key}/transitions", user_id,
    )
    transitions = resp.json().get("transitions", [])
    target = next((t for t in transitions if t["name"].lower() == transition_name.lower()), None)
    if not target:
        available = ", ".join(t["name"] for t in transitions)
        return f"Transition '{transition_name}' not found. Available: {available}"

    await _jira().api_request(
        "post", f"/rest/api/3/issue/{issue_key}/transitions", user_id,
        json={"transition": {"id": target["id"]}},
    )
    return f"Issue {issue_key} transitioned to {transition_name}"
