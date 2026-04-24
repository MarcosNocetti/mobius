import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


def _teams():
    return integration_registry.get("teams")


@tool_action(
    name="send_teams_message",
    description="Send a message to a Microsoft Teams chat.",
    integration="teams",
    params={
        "chat_id": {"type": "string", "description": "Chat ID"},
        "text": {"type": "string", "description": "Message text"},
    },
)
async def send_teams_message(user_id: str, chat_id: str, text: str) -> str:
    resp = await _teams().api_request(
        "post", f"/chats/{chat_id}/messages", user_id,
        json={"body": {"content": text}},
    )
    result = resp.json()
    return f"Message sent: {result.get('id')}"


@tool_action(
    name="list_teams",
    description="List Microsoft Teams the user has joined.",
    integration="teams",
    params={},
)
async def list_teams(user_id: str) -> str:
    resp = await _teams().api_request("get", "/me/joinedTeams", user_id)
    teams = [
        {"id": t["id"], "displayName": t["displayName"]}
        for t in resp.json().get("value", [])
    ]
    return json.dumps(teams, ensure_ascii=False)


@tool_action(
    name="create_teams_meeting",
    description="Create a Microsoft Teams online meeting.",
    integration="teams",
    params={
        "subject": {"type": "string", "description": "Meeting subject"},
        "start_dt": {"type": "string", "description": "Start datetime ISO 8601"},
        "end_dt": {"type": "string", "description": "End datetime ISO 8601"},
    },
)
async def create_teams_meeting(user_id: str, subject: str, start_dt: str, end_dt: str) -> str:
    resp = await _teams().api_request(
        "post", "/me/onlineMeetings", user_id,
        json={
            "subject": subject,
            "startDateTime": start_dt,
            "endDateTime": end_dt,
        },
    )
    result = resp.json()
    return f"Meeting created: {result.get('id')} — {result.get('joinWebUrl', '')}"
