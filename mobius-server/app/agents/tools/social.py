from app.integrations.twitter import post_tweet as _post_tweet
from app.integrations.instagram import post_photo as _post_photo


async def post_twitter_tool(user_id: str, text: str) -> str:
    """Post a tweet on Twitter/X. Returns tweet ID."""
    result = await _post_tweet(user_id, text)
    tweet_id = result.get("data", {}).get("id", "unknown")
    return f"Tweet posted: {tweet_id}"


async def post_instagram_tool(user_id: str, image_url: str, caption: str) -> str:
    """Post a photo to Instagram. Returns media ID."""
    result = await _post_photo(user_id, image_url, caption)
    return f"Instagram post created: {result.get('id')}"
