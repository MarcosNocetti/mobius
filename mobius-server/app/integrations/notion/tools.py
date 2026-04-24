import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


@tool_action(
    name="create_notion_page",
    description="Create a page in Notion with a title and text content.",
    integration="notion",
    params={
        "title": {"type": "string", "description": "Page title"},
        "content": {"type": "string", "description": "Page content"},
    },
)
async def create_notion_page(user_id: str, title: str, content: str) -> str:
    page_body = {
        "parent": {"type": "workspace", "workspace": True},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]}
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            }
        ],
    }
    resp = await integration_registry.get("notion").api_request(
        "post", "https://api.notion.com/v1/pages",
        user_id, json=page_body,
    )
    result = resp.json()
    return f"Notion page created: {result.get('url', result.get('id'))}"
