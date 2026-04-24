import json

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry
from app.core.redis import redis_client


@tool_action(
    name="post_instagram",
    description="Post a photo to Instagram. Requires a publicly accessible image URL.",
    integration="instagram",
    params={
        "image_url": {"type": "string", "description": "Public URL of the image to post"},
        "caption": {"type": "string", "description": "Post caption"},
    },
)
async def post_instagram(user_id: str, image_url: str, caption: str) -> str:
    # Instagram requires the ig_user_id stored alongside the token
    raw = await redis_client.get(f"oauth:instagram:{user_id}")
    if not raw:
        return "Instagram not connected."
    data = json.loads(raw if isinstance(raw, str) else raw.decode())
    ig_id = data.get("ig_user_id")
    token = data.get("access_token")
    if not ig_id or not token:
        return "Instagram account ID not found. Please reconnect."

    import httpx
    async with httpx.AsyncClient() as client:
        # Step 1: create media container
        container = await client.post(
            f"https://graph.facebook.com/v19.0/{ig_id}/media",
            params={"image_url": image_url, "caption": caption, "access_token": token},
        )
        container.raise_for_status()
        container_id = container.json()["id"]

        # Step 2: publish
        publish = await client.post(
            f"https://graph.facebook.com/v19.0/{ig_id}/media_publish",
            params={"creation_id": container_id, "access_token": token},
        )
        publish.raise_for_status()
        result = publish.json()

    return f"Instagram post created: {result.get('id')}"
