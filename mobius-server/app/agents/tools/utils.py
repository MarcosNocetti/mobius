import httpx


async def web_search(query: str) -> str:
    """Search DuckDuckGo Instant Answer API and return a text summary."""
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
    data = resp.json()
    abstract = data.get("AbstractText") or data.get("Answer") or ""
    if not abstract:
        related = data.get("RelatedTopics", [])
        if related and isinstance(related[0], dict):
            abstract = related[0].get("Text", "No result found.")
    return abstract or "No result found."


async def summarize(text: str, model: str = "gemini/gemini-2.0-flash", api_key: str | None = None) -> str:
    """Summarize text using LLM."""
    import litellm
    from app.core.config import settings
    response = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": f"Summarize the following:\n\n{text}"}],
        api_key=api_key or settings.GEMINI_API_KEY,
    )
    return response.choices[0].message.content or ""
