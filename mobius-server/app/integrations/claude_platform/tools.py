import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


def _claude():
    return integration_registry.get("claude_platform")


@tool_action(
    name="create_claude_batch",
    description="Create a batch of Claude messages for async processing.",
    integration="claude_platform",
    params={
        "prompts": {"type": "array", "items": {"type": "string"}, "description": "List of prompts to process"},
        "model": {"type": "string", "description": "Model to use (default: claude-sonnet-4-6)"},
    },
)
async def create_claude_batch(user_id: str, prompts: list[str], model: str = "claude-sonnet-4-6") -> str:
    requests = []
    for i, prompt in enumerate(prompts):
        requests.append({
            "custom_id": f"req-{i}",
            "params": {
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
        })
    resp = await _claude().api_request(
        "post", "/messages/batches", user_id, json={"requests": requests},
    )
    result = resp.json()
    return f"Batch created: {result.get('id')} — {len(prompts)} requests"


@tool_action(
    name="get_claude_batch_status",
    description="Get the status of a Claude message batch.",
    integration="claude_platform",
    params={
        "batch_id": {"type": "string", "description": "Batch ID"},
    },
)
async def get_claude_batch_status(user_id: str, batch_id: str) -> str:
    resp = await _claude().api_request(
        "get", f"/messages/batches/{batch_id}", user_id,
    )
    result = resp.json()
    return f"Batch {batch_id}: status={result.get('processing_status', 'unknown')}, counts={json.dumps(result.get('request_counts', {}))}"
