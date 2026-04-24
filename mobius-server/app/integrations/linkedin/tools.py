import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry
from app.core.redis import redis_client


@tool_action(
    name="post_linkedin",
    description="Post a text update to LinkedIn.",
    integration="linkedin",
    params={
        "text": {"type": "string", "description": "Post text content"},
    },
)
async def post_linkedin(user_id: str, text: str) -> str:
    # LinkedIn requires person_urn stored alongside token
    raw = await redis_client.get(f"oauth:linkedin:{user_id}")
    if not raw:
        return "LinkedIn not connected."
    data = json.loads(raw if isinstance(raw, str) else raw.decode())
    token = data.get("access_token")
    person_urn = data.get("person_urn")
    if not person_urn or not token:
        return "LinkedIn profile not found. Please reconnect."

    share_body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=share_body,
        )
        resp.raise_for_status()
        result = resp.json()

    return f"LinkedIn post created: {result.get('id')}"
