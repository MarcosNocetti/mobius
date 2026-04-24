"""
Tool registry — maps tool names to (function, JSON schema) pairs.
Each tool function receives user_id as first arg (injected by engine),
plus whatever args the LLM provides.
"""
from app.integrations.google.tools import (
    create_calendar_event, list_calendar_events,
    send_gmail, read_gmail,
    create_google_doc, create_spreadsheet,
    list_drive_files, create_task, list_tasks,
)
from app.integrations.twitter.tools import post_tweet
from app.integrations.notion.tools import create_notion_page


def _tool(name: str, desc: str, fn, params: dict) -> dict:
    return {
        "fn": fn,
        "schema": {
            "type": "function",
            "function": {"name": name, "description": desc, "parameters": params},
        },
    }


def _props(**fields) -> dict:
    return {"type": "object", "properties": fields, "required": list(fields.keys())}


def get_tools_for_user(user_id: str) -> dict:
    uid = user_id
    return {
        # --- Google Calendar ---
        "create_calendar_event": _tool(
            "create_calendar_event",
            "Create an event on Google Calendar. Use ISO 8601 datetime (e.g. 2026-04-24T10:00:00-03:00).",
            lambda title, start_dt, end_dt: create_calendar_event(uid, title, start_dt, end_dt),
            _props(
                title={"type": "string", "description": "Event title"},
                start_dt={"type": "string", "description": "Start datetime ISO 8601"},
                end_dt={"type": "string", "description": "End datetime ISO 8601"},
            ),
        ),
        "list_calendar_events": _tool(
            "list_calendar_events",
            "List upcoming Google Calendar events. Use ISO 8601 for time_min/time_max.",
            lambda time_min, time_max: list_calendar_events(uid, time_min, time_max),
            _props(
                time_min={"type": "string", "description": "Start of range ISO 8601"},
                time_max={"type": "string", "description": "End of range ISO 8601"},
            ),
        ),
        # --- Gmail ---
        "send_gmail": _tool(
            "send_gmail",
            "Send an email via Gmail.",
            lambda to, subject, body: send_gmail(uid, to, subject, body),
            _props(
                to={"type": "string", "description": "Recipient email"},
                subject={"type": "string", "description": "Subject line"},
                body={"type": "string", "description": "Email body"},
            ),
        ),
        "read_gmail": _tool(
            "read_gmail",
            "Search and read Gmail messages. Use Gmail search syntax (e.g. 'is:unread', 'from:boss@company.com', 'subject:meeting').",
            lambda query="is:unread": read_gmail(uid, query),
            {"type": "object", "properties": {"query": {"type": "string", "description": "Gmail search query (default: is:unread)"}}, "required": []},
        ),
        # --- Google Docs ---
        "create_google_doc": _tool(
            "create_google_doc",
            "Create a Google Doc with a title and text content. Returns the document URL.",
            lambda title, content: create_google_doc(uid, title, content),
            _props(
                title={"type": "string", "description": "Document title"},
                content={"type": "string", "description": "Document text content"},
            ),
        ),
        # --- Google Sheets ---
        "create_spreadsheet": _tool(
            "create_spreadsheet",
            "Create a Google Spreadsheet. Optionally provide initial data as a 2D array of strings.",
            lambda title, data=None: create_spreadsheet(uid, title, data),
            {"type": "object", "properties": {
                "title": {"type": "string", "description": "Spreadsheet title"},
                "data": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}, "description": "Initial data rows (optional)"},
            }, "required": ["title"]},
        ),
        # --- Google Drive ---
        "list_drive_files": _tool(
            "list_drive_files",
            "Search files in Google Drive by name.",
            lambda query="": list_drive_files(uid, query),
            {"type": "object", "properties": {"query": {"type": "string", "description": "Search query (file name)"}}, "required": []},
        ),
        # --- Google Tasks ---
        "create_task": _tool(
            "create_task",
            "Create a Google Task with title and optional notes/due date.",
            lambda title, notes="", due="": create_task(uid, title, notes, due),
            {"type": "object", "properties": {
                "title": {"type": "string", "description": "Task title"},
                "notes": {"type": "string", "description": "Task notes (optional)"},
                "due": {"type": "string", "description": "Due date ISO 8601 (optional)"},
            }, "required": ["title"]},
        ),
        "list_tasks": _tool(
            "list_tasks",
            "List Google Tasks.",
            lambda: list_tasks(uid),
            {"type": "object", "properties": {}, "required": []},
        ),
        # --- Twitter ---
        "post_tweet": _tool(
            "post_tweet",
            "Post a tweet on Twitter/X (max 280 chars).",
            lambda text: post_tweet(uid, text),
            _props(text={"type": "string", "description": "Tweet text"}),
        ),
        # --- Notion ---
        "create_notion_page": _tool(
            "create_notion_page",
            "Create a page in Notion.",
            lambda title, content: create_notion_page(uid, title, content),
            _props(
                title={"type": "string", "description": "Page title"},
                content={"type": "string", "description": "Page content"},
            ),
        ),
    }
