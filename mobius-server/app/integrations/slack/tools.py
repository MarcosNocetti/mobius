import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


def _slack():
    return integration_registry.get("slack")


@tool_action(
    name="send_slack_message",
    description="Send a message to a Slack channel.",
    integration="slack",
    params={
        "channel": {"type": "string", "description": "Channel ID or name"},
        "text": {"type": "string", "description": "Message text"},
    },
)
async def send_slack_message(user_id: str, channel: str, text: str) -> str:
    resp = await _slack().api_request(
        "post", "https://slack.com/api/chat.postMessage", user_id,
        json={"channel": channel, "text": text},
    )
    data = resp.json()
    if data.get("ok"):
        return f"Message sent to {channel}: ts={data.get('ts')}"
    return f"Slack error: {data.get('error', 'unknown')}"


@tool_action(
    name="read_slack_channel",
    description="Read recent messages from a Slack channel.",
    integration="slack",
    params={
        "channel": {"type": "string", "description": "Channel ID"},
        "limit": {"type": "integer", "description": "Number of messages (default 10)"},
    },
)
async def read_slack_channel(user_id: str, channel: str, limit: int = 10) -> str:
    resp = await _slack().api_request(
        "get", "https://slack.com/api/conversations.history", user_id,
        params={"channel": channel, "limit": limit},
    )
    data = resp.json()
    if not data.get("ok"):
        return f"Slack error: {data.get('error', 'unknown')}"
    messages = [
        {"user": m.get("user", ""), "text": m.get("text", ""), "ts": m.get("ts", "")}
        for m in data.get("messages", [])
    ]
    return json.dumps(messages, ensure_ascii=False)


@tool_action(
    name="list_slack_channels",
    description="List Slack channels.",
    integration="slack",
    params={},
)
async def list_slack_channels(user_id: str) -> str:
    resp = await _slack().api_request(
        "get", "https://slack.com/api/conversations.list", user_id,
    )
    data = resp.json()
    if not data.get("ok"):
        return f"Slack error: {data.get('error', 'unknown')}"
    channels = [
        {"id": c["id"], "name": c["name"]}
        for c in data.get("channels", [])
    ]
    return json.dumps(channels, ensure_ascii=False)


@tool_action(
    name="search_slack_messages",
    description="Search messages in Slack.",
    integration="slack",
    params={
        "query": {"type": "string", "description": "Search query"},
    },
)
async def search_slack_messages(user_id: str, query: str) -> str:
    resp = await _slack().api_request(
        "get", "https://slack.com/api/search.messages", user_id,
        params={"query": query},
    )
    data = resp.json()
    if not data.get("ok"):
        return f"Slack error: {data.get('error', 'unknown')}"
    matches = data.get("messages", {}).get("matches", [])
    results = [
        {"text": m.get("text", ""), "channel": m.get("channel", {}).get("name", ""), "ts": m.get("ts", "")}
        for m in matches[:10]
    ]
    return json.dumps(results, ensure_ascii=False)
