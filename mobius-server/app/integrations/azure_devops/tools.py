import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


def _azdo():
    return integration_registry.get("azure_devops")


@tool_action(
    name="create_work_item",
    description="Create a work item in Azure DevOps.",
    integration="azure_devops",
    params={
        "organization": {"type": "string", "description": "Azure DevOps organization"},
        "project": {"type": "string", "description": "Project name"},
        "type": {"type": "string", "description": "Work item type (e.g. Task, Bug)"},
        "title": {"type": "string", "description": "Work item title"},
        "description": {"type": "string", "description": "Work item description"},
    },
)
async def create_work_item(user_id: str, organization: str, project: str, type: str, title: str, description: str) -> str:
    resp = await _azdo().api_request(
        "post",
        f"/{organization}/{project}/_apis/wit/workitems/${type}",
        user_id,
        json=[
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.Description", "value": description},
        ],
        headers={"Content-Type": "application/json-patch+json"},
        params={"api-version": "7.0"},
    )
    result = resp.json()
    return f"Work item created: #{result.get('id')} — {title}"


@tool_action(
    name="list_work_items",
    description="Query work items in Azure DevOps using WIQL.",
    integration="azure_devops",
    params={
        "organization": {"type": "string", "description": "Azure DevOps organization"},
        "project": {"type": "string", "description": "Project name"},
        "query": {"type": "string", "description": "WIQL query string"},
    },
)
async def list_work_items(user_id: str, organization: str, project: str, query: str) -> str:
    resp = await _azdo().api_request(
        "post",
        f"/{organization}/{project}/_apis/wit/wiql",
        user_id,
        json={"query": query},
        params={"api-version": "7.0"},
    )
    items = resp.json().get("workItems", [])
    results = [{"id": i["id"], "url": i.get("url", "")} for i in items[:20]]
    return json.dumps(results, ensure_ascii=False)


@tool_action(
    name="trigger_pipeline",
    description="Trigger a pipeline run in Azure DevOps.",
    integration="azure_devops",
    params={
        "organization": {"type": "string", "description": "Azure DevOps organization"},
        "project": {"type": "string", "description": "Project name"},
        "pipeline_id": {"type": "string", "description": "Pipeline ID"},
    },
)
async def trigger_pipeline(user_id: str, organization: str, project: str, pipeline_id: str) -> str:
    resp = await _azdo().api_request(
        "post",
        f"/{organization}/{project}/_apis/pipelines/{pipeline_id}/runs",
        user_id,
        json={},
        params={"api-version": "7.0"},
    )
    result = resp.json()
    return f"Pipeline run started: #{result.get('id')} — state: {result.get('state', 'unknown')}"
