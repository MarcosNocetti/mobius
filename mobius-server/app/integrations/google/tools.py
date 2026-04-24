import json
import base64
from email.mime.text import MIMEText

from app.agents.tools.decorator import tool_action
from app.integrations.registry import integration_registry


def _google():
    return integration_registry.get("google")


@tool_action(
    name="create_calendar_event",
    description="Create an event on Google Calendar. Use ISO 8601 datetime (e.g. 2026-04-24T10:00:00-03:00).",
    integration="google",
    params={
        "title": {"type": "string", "description": "Event title"},
        "start_dt": {"type": "string", "description": "Start datetime ISO 8601"},
        "end_dt": {"type": "string", "description": "End datetime ISO 8601"},
    },
)
async def create_calendar_event(user_id: str, title: str, start_dt: str, end_dt: str) -> str:
    event_body = {
        "summary": title,
        "start": {"dateTime": start_dt, "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": end_dt, "timeZone": "America/Sao_Paulo"},
    }
    resp = await _google().api_request(
        "post", "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        user_id, json=event_body,
    )
    result = resp.json()
    return f"Event created: {result.get('id')} — {result.get('summary')}"


@tool_action(
    name="list_calendar_events",
    description="List upcoming Google Calendar events. Use ISO 8601 for time_min/time_max.",
    integration="google",
    params={
        "time_min": {"type": "string", "description": "Start of range ISO 8601"},
        "time_max": {"type": "string", "description": "End of range ISO 8601"},
    },
)
async def list_calendar_events(user_id: str, time_min: str, time_max: str) -> str:
    resp = await _google().api_request(
        "get", "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        user_id, params={
            "timeMin": time_min, "timeMax": time_max,
            "maxResults": 10, "singleEvents": "true", "orderBy": "startTime",
        },
    )
    events = resp.json().get("items", [])
    items = [
        {"id": e["id"], "summary": e.get("summary", ""), "start": e.get("start", {}), "end": e.get("end", {})}
        for e in events
    ]
    return json.dumps(items, ensure_ascii=False)


@tool_action(
    name="send_gmail",
    description="Send an email via Gmail.",
    integration="google",
    params={
        "to": {"type": "string", "description": "Recipient email"},
        "subject": {"type": "string", "description": "Subject line"},
        "body": {"type": "string", "description": "Email body"},
    },
)
async def send_gmail(user_id: str, to: str, subject: str, body: str) -> str:
    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    resp = await _google().api_request(
        "post", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        user_id, json={"raw": raw},
    )
    result = resp.json()
    return f"Email sent: {result.get('id')}"


@tool_action(
    name="read_gmail",
    description="Search and read Gmail messages. Use Gmail search syntax (e.g. 'is:unread', 'from:boss@company.com').",
    integration="google",
    params={
        "query": {"type": "string", "description": "Gmail search query (default: is:unread)"},
    },
)
async def read_gmail(user_id: str, query: str = "is:unread") -> str:
    resp = await _google().api_request(
        "get", "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        user_id, params={"q": query, "maxResults": 5},
    )
    messages = resp.json().get("messages", [])
    results = []
    for msg in messages[:5]:
        detail = await _google().api_request(
            "get", f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
            user_id, params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
        )
        headers = {h["name"]: h["value"] for h in detail.json().get("payload", {}).get("headers", [])}
        results.append({
            "id": msg["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
        })
    return json.dumps(results, ensure_ascii=False)


@tool_action(
    name="create_google_doc",
    description="Create a Google Doc with a title and text content. Returns the document URL.",
    integration="google",
    params={
        "title": {"type": "string", "description": "Document title"},
        "content": {"type": "string", "description": "Document text content"},
    },
)
async def create_google_doc(user_id: str, title: str, content: str) -> str:
    resp = await _google().api_request(
        "post", "https://docs.googleapis.com/v1/documents",
        user_id, json={"title": title},
    )
    doc = resp.json()
    doc_id = doc["documentId"]
    if content:
        await _google().api_request(
            "post", f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
            user_id, json={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        )
    return f"Doc created: {title} — https://docs.google.com/document/d/{doc_id}"


@tool_action(
    name="create_spreadsheet",
    description="Create a Google Spreadsheet. Optionally provide initial data as a 2D array of strings.",
    integration="google",
    params={
        "title": {"type": "string", "description": "Spreadsheet title"},
        "data": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}, "description": "Initial data rows (optional)"},
    },
)
async def create_spreadsheet(user_id: str, title: str, data: list[list[str]] | None = None) -> str:
    resp = await _google().api_request(
        "post", "https://sheets.googleapis.com/v4/spreadsheets",
        user_id, json={"properties": {"title": title}},
    )
    sheet = resp.json()
    sheet_id = sheet["spreadsheetId"]
    if data:
        await _google().api_request(
            "put", f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/A1",
            user_id, params={"valueInputOption": "RAW"}, json={"values": data},
        )
    return f"Spreadsheet created: {title} — https://docs.google.com/spreadsheets/d/{sheet_id}"


@tool_action(
    name="list_drive_files",
    description="Search files in Google Drive by name.",
    integration="google",
    params={
        "query": {"type": "string", "description": "Search query (file name)"},
    },
)
async def list_drive_files(user_id: str, query: str = "") -> str:
    params = {"pageSize": 10, "fields": "files(id,name,mimeType,webViewLink,modifiedTime)"}
    if query:
        params["q"] = f"name contains '{query}'"
    resp = await _google().api_request(
        "get", "https://www.googleapis.com/drive/v3/files",
        user_id, params=params,
    )
    files = resp.json().get("files", [])
    return json.dumps(files, ensure_ascii=False)


@tool_action(
    name="create_task",
    description="Create a Google Task with title and optional notes/due date.",
    integration="google",
    params={
        "title": {"type": "string", "description": "Task title"},
        "notes": {"type": "string", "description": "Task notes (optional)"},
        "due": {"type": "string", "description": "Due date ISO 8601 (optional)"},
    },
)
async def create_task(user_id: str, title: str, notes: str = "", due: str = "") -> str:
    task_body = {"title": title}
    if notes:
        task_body["notes"] = notes
    if due:
        task_body["due"] = due
    resp = await _google().api_request(
        "post", "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks",
        user_id, json=task_body,
    )
    result = resp.json()
    return f"Task created: {result.get('id')} — {result.get('title')}"


@tool_action(
    name="list_tasks",
    description="List Google Tasks.",
    integration="google",
    params={},
)
async def list_tasks(user_id: str) -> str:
    resp = await _google().api_request(
        "get", "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks",
        user_id, params={"maxResults": 10},
    )
    tasks = [
        {"id": t["id"], "title": t.get("title", ""), "status": t.get("status", ""), "due": t.get("due", "")}
        for t in resp.json().get("items", [])
    ]
    return json.dumps(tasks, ensure_ascii=False)
