import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


def _n8n():
    return integration_registry.get("n8n")


@tool_action(
    name="list_n8n_workflows",
    description="List all workflows in n8n.",
    integration="n8n",
    params={},
)
async def list_n8n_workflows(user_id: str) -> str:
    resp = await _n8n().api_request("get", "/workflows", user_id)
    workflows = [
        {"id": w["id"], "name": w["name"], "active": w.get("active", False)}
        for w in resp.json().get("data", [])
    ]
    return json.dumps(workflows, ensure_ascii=False)


@tool_action(
    name="execute_n8n_workflow",
    description="Execute a workflow in n8n.",
    integration="n8n",
    params={
        "workflow_id": {"type": "string", "description": "Workflow ID"},
    },
)
async def execute_n8n_workflow(user_id: str, workflow_id: str) -> str:
    resp = await _n8n().api_request(
        "post", f"/workflows/{workflow_id}/execute", user_id,
    )
    result = resp.json()
    return f"Workflow {workflow_id} executed: {result.get('data', {}).get('executionId', 'unknown')}"
