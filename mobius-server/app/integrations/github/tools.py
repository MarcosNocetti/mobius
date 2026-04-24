import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


def _github():
    return integration_registry.get("github")


@tool_action(
    name="create_github_issue",
    description="Create an issue on a GitHub repository.",
    integration="github",
    params={
        "repo": {"type": "string", "description": "Repository full name (owner/repo)"},
        "title": {"type": "string", "description": "Issue title"},
        "body": {"type": "string", "description": "Issue body"},
    },
)
async def create_github_issue(user_id: str, repo: str, title: str, body: str) -> str:
    resp = await _github().api_request(
        "post", f"/repos/{repo}/issues", user_id, json={"title": title, "body": body}
    )
    result = resp.json()
    return f"Issue created: #{result.get('number')} — {result.get('title')}"


@tool_action(
    name="list_github_issues",
    description="List issues on a GitHub repository.",
    integration="github",
    params={
        "repo": {"type": "string", "description": "Repository full name (owner/repo)"},
        "state": {"type": "string", "description": "Issue state: open, closed, all (default: open)"},
    },
)
async def list_github_issues(user_id: str, repo: str, state: str = "open") -> str:
    resp = await _github().api_request(
        "get", f"/repos/{repo}/issues", user_id, params={"state": state}
    )
    issues = [
        {"number": i["number"], "title": i["title"], "state": i["state"]}
        for i in resp.json()
    ]
    return json.dumps(issues, ensure_ascii=False)


@tool_action(
    name="create_pull_request",
    description="Create a pull request on a GitHub repository.",
    integration="github",
    params={
        "repo": {"type": "string", "description": "Repository full name (owner/repo)"},
        "title": {"type": "string", "description": "PR title"},
        "body": {"type": "string", "description": "PR body"},
        "head": {"type": "string", "description": "Head branch"},
        "base": {"type": "string", "description": "Base branch"},
    },
)
async def create_pull_request(user_id: str, repo: str, title: str, body: str, head: str, base: str) -> str:
    resp = await _github().api_request(
        "post", f"/repos/{repo}/pulls", user_id,
        json={"title": title, "body": body, "head": head, "base": base},
    )
    result = resp.json()
    return f"PR created: #{result.get('number')} — {result.get('title')}"


@tool_action(
    name="list_pull_requests",
    description="List pull requests on a GitHub repository.",
    integration="github",
    params={
        "repo": {"type": "string", "description": "Repository full name (owner/repo)"},
        "state": {"type": "string", "description": "PR state: open, closed, all (default: open)"},
    },
)
async def list_pull_requests(user_id: str, repo: str, state: str = "open") -> str:
    resp = await _github().api_request(
        "get", f"/repos/{repo}/pulls", user_id, params={"state": state}
    )
    prs = [
        {"number": p["number"], "title": p["title"], "state": p["state"]}
        for p in resp.json()
    ]
    return json.dumps(prs, ensure_ascii=False)


@tool_action(
    name="list_repos",
    description="List repositories for the authenticated GitHub user.",
    integration="github",
    params={},
)
async def list_repos(user_id: str) -> str:
    resp = await _github().api_request("get", "/user/repos", user_id)
    repos = [
        {"full_name": r["full_name"], "private": r["private"], "description": r.get("description", "")}
        for r in resp.json()
    ]
    return json.dumps(repos, ensure_ascii=False)


@tool_action(
    name="search_code",
    description="Search code on GitHub.",
    integration="github",
    params={
        "query": {"type": "string", "description": "Search query"},
    },
)
async def search_code(user_id: str, query: str) -> str:
    resp = await _github().api_request(
        "get", "/search/code", user_id, params={"q": query}
    )
    items = resp.json().get("items", [])
    results = [
        {"name": i["name"], "path": i["path"], "repo": i["repository"]["full_name"]}
        for i in items[:10]
    ]
    return json.dumps(results, ensure_ascii=False)
