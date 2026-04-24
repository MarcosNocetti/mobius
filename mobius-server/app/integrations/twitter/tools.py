from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


@tool_action(
    name="post_tweet",
    description="Post a tweet on Twitter/X (max 280 chars).",
    integration="twitter",
    params={
        "text": {"type": "string", "description": "Tweet text"},
    },
)
async def post_tweet(user_id: str, text: str) -> str:
    resp = await integration_registry.get("twitter").api_request(
        "post", "https://api.twitter.com/2/tweets",
        user_id, json={"text": text},
    )
    result = resp.json()
    tweet_id = result.get("data", {}).get("id", "unknown")
    return f"Tweet posted: {tweet_id}"
