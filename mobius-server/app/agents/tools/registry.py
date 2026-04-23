"""
Tool registry — maps tool names to (function, JSON schema) pairs.
Each tool function receives user_id as first arg (injected by engine),
plus whatever args the LLM provides.
"""
from app.integrations.google import create_calendar_event, send_gmail
from app.integrations.twitter import post_tweet
from app.integrations.notion import create_notion_page


def get_tools_for_user(user_id: str) -> dict:
    """
    Returns {name: {"fn": async_callable, "schema": openai_tool_schema}}
    with user_id pre-bound into each function.
    """
    return {
        "create_calendar_event": {
            "fn": lambda title, start_dt, end_dt: create_calendar_event(user_id, title, start_dt, end_dt),
            "schema": {
                "type": "function",
                "function": {
                    "name": "create_calendar_event",
                    "description": "Create an event on the user's Google Calendar. Use ISO 8601 datetime format (e.g. 2026-04-23T10:00:00-03:00).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Event title/summary"},
                            "start_dt": {"type": "string", "description": "Start datetime in ISO 8601 format"},
                            "end_dt": {"type": "string", "description": "End datetime in ISO 8601 format"},
                        },
                        "required": ["title", "start_dt", "end_dt"],
                    },
                },
            },
        },
        "send_gmail": {
            "fn": lambda to, subject, body: send_gmail(user_id, to, subject, body),
            "schema": {
                "type": "function",
                "function": {
                    "name": "send_gmail",
                    "description": "Send an email via the user's Gmail account.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject line"},
                            "body": {"type": "string", "description": "Email body text"},
                        },
                        "required": ["to", "subject", "body"],
                    },
                },
            },
        },
        "post_tweet": {
            "fn": lambda text: post_tweet(user_id, text),
            "schema": {
                "type": "function",
                "function": {
                    "name": "post_tweet",
                    "description": "Post a tweet on the user's Twitter/X account.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Tweet text (max 280 chars)"},
                        },
                        "required": ["text"],
                    },
                },
            },
        },
        "create_notion_page": {
            "fn": lambda title, content: create_notion_page(user_id, title, content),
            "schema": {
                "type": "function",
                "function": {
                    "name": "create_notion_page",
                    "description": "Create a new page in the user's Notion workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Page title"},
                            "content": {"type": "string", "description": "Page content (plain text)"},
                        },
                        "required": ["title", "content"],
                    },
                },
            },
        },
    }
