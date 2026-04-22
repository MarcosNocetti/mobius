from app.integrations.twitter import post_tweet as _post_tweet


async def post_twitter_tool(user_id: str, text: str) -> str:
    """Post a tweet on Twitter/X. Returns tweet ID."""
    result = await _post_tweet(user_id, text)
    tweet_id = result.get("data", {}).get("id", "unknown")
    return f"Tweet posted: {tweet_id}"
