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


# ===== Gmail Label/Folder Management =====

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


@tool_action(
    name="list_gmail_labels",
    description="List all Gmail labels (folders/categories) for the user.",
    integration="google",
    params={},
)
async def list_gmail_labels(user_id: str) -> str:
    resp = await _google().api_request("get", f"{GMAIL_API}/labels", user_id)
    labels = resp.json().get("labels", [])
    lines = []
    for l in sorted(labels, key=lambda x: x.get("name", "")):
        ltype = l.get("type", "user")
        count = l.get("messagesTotal", "")
        unread = l.get("messagesUnread", "")
        info = f" ({count} msgs, {unread} unread)" if count else ""
        lines.append(f"- {l['name']} [id={l['id']}] ({ltype}){info}")
    return "\n".join(lines) if lines else "No labels found"


@tool_action(
    name="create_gmail_label",
    description="Create a new Gmail label (folder). Use for organizing emails.",
    integration="google",
    params={
        "name": {"type": "string", "description": "Label name (e.g. 'Work/Projects' for nested)"},
    },
)
async def create_gmail_label(user_id: str, name: str) -> str:
    resp = await _google().api_request("post", f"{GMAIL_API}/labels", user_id, json={
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    })
    data = resp.json()
    return f"Label created: '{data['name']}' (id={data['id']})"


@tool_action(
    name="delete_gmail_label",
    description="Delete a Gmail label by its ID. Cannot delete system labels.",
    integration="google",
    params={
        "label_id": {"type": "string", "description": "Label ID to delete"},
    },
)
async def delete_gmail_label(user_id: str, label_id: str) -> str:
    await _google().api_request("delete", f"{GMAIL_API}/labels/{label_id}", user_id)
    return f"Label {label_id} deleted"


@tool_action(
    name="apply_gmail_label",
    description="Apply a label to Gmail messages. Use to organize/categorize emails.",
    integration="google",
    params={
        "message_ids": {"type": "array", "items": {"type": "string"}, "description": "List of message IDs"},
        "label_ids_to_add": {"type": "array", "items": {"type": "string"}, "description": "Label IDs to add"},
        "label_ids_to_remove": {"type": "array", "items": {"type": "string"}, "description": "Label IDs to remove (optional)"},
    },
)
async def apply_gmail_label(user_id: str, message_ids: list, label_ids_to_add: list, label_ids_to_remove: list = None) -> str:
    body = {
        "ids": message_ids,
        "addLabelIds": label_ids_to_add,
    }
    if label_ids_to_remove:
        body["removeLabelIds"] = label_ids_to_remove
    await _google().api_request("post", f"{GMAIL_API}/messages/batchModify", user_id, json=body)
    return f"Labels applied to {len(message_ids)} message(s)"


@tool_action(
    name="move_gmail_to_folder",
    description="Move Gmail messages to a specific folder/label. Removes from INBOX if moving elsewhere.",
    integration="google",
    params={
        "query": {"type": "string", "description": "Gmail search query to find messages (e.g. 'from:newsletter@co.com')"},
        "target_label": {"type": "string", "description": "Label name to move to (will create if not exists)"},
    },
)
async def move_gmail_to_folder(user_id: str, query: str, target_label: str) -> str:
    # Find messages matching query
    resp = await _google().api_request("get", f"{GMAIL_API}/messages", user_id,
                                        params={"q": query, "maxResults": 50})
    messages = resp.json().get("messages", [])
    if not messages:
        return f"No messages matching '{query}'"

    # Find or create target label
    labels_resp = await _google().api_request("get", f"{GMAIL_API}/labels", user_id)
    labels = labels_resp.json().get("labels", [])
    target = next((l for l in labels if l["name"].lower() == target_label.lower()), None)

    if not target:
        create_resp = await _google().api_request("post", f"{GMAIL_API}/labels", user_id, json={
            "name": target_label, "labelListVisibility": "labelShow", "messageListVisibility": "show",
        })
        target = create_resp.json()

    # Apply label and remove from INBOX
    msg_ids = [m["id"] for m in messages]
    await _google().api_request("post", f"{GMAIL_API}/messages/batchModify", user_id, json={
        "ids": msg_ids,
        "addLabelIds": [target["id"]],
        "removeLabelIds": ["INBOX"],
    })
    return f"Moved {len(msg_ids)} message(s) to '{target_label}'"


@tool_action(
    name="organize_gmail",
    description="Smart email organization: reads emails, uses AI to categorize them by topic, creates labels, and moves each email to the right folder. Fully automatic.",
    integration="google",
    params={
        "query": {"type": "string", "description": "Gmail search query (default: 'is:unread in:inbox')"},
    },
)
async def organize_gmail(user_id: str, query: str = "is:unread in:inbox") -> str:
    import litellm
    from app.agents.engine import _get_gemini_key

    # 1. Get messages
    resp = await _google().api_request("get", f"{GMAIL_API}/messages", user_id,
                                        params={"q": query, "maxResults": 30})
    messages = resp.json().get("messages", [])
    if not messages:
        return "No messages to organize"

    # 2. Get details for each message
    email_data = []
    for msg in messages[:30]:
        detail = await _google().api_request("get", f"{GMAIL_API}/messages/{msg['id']}", user_id,
                                              params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]})
        headers = {h["name"]: h["value"] for h in detail.json().get("payload", {}).get("headers", [])}
        email_data.append({
            "id": msg["id"],
            "from": headers.get("From", "unknown"),
            "subject": headers.get("Subject", "no subject"),
            "date": headers.get("Date", ""),
        })

    # 3. Ask AI to categorize
    email_list = "\n".join(f"ID:{e['id']} | From: {e['from']} | Subject: {e['subject']}" for e in email_data)

    categorize_prompt = f"""Categorize these emails into folders. Return ONLY a JSON array where each item has "id" (email ID) and "label" (folder name).
Use clear, short folder names in Portuguese like: "Newsletters", "Trabalho", "Social", "Compras", "Financeiro", "Notificações", "Pessoal", "Importante".

Emails:
{email_list}

Return ONLY the JSON array, no explanation. Example: [{{"id":"abc123","label":"Newsletters"}},{{"id":"def456","label":"Trabalho"}}]"""

    ai_resp = await litellm.acompletion(
        model="gemini/gemini-2.5-flash",
        messages=[{"role": "user", "content": categorize_prompt}],
        api_key=_get_gemini_key(),
    )
    raw = ai_resp.choices[0].message.content.strip()

    # Parse AI response
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    categories = json.loads(raw)

    # 4. Get existing labels
    labels_resp = await _google().api_request("get", f"{GMAIL_API}/labels", user_id)
    existing_labels = {l["name"].lower(): l for l in labels_resp.json().get("labels", [])}

    # 5. Group by label and apply
    label_groups = {}
    for cat in categories:
        label_name = cat["label"]
        msg_id = cat["id"]
        label_groups.setdefault(label_name, []).append(msg_id)

    results = []
    for label_name, msg_ids in label_groups.items():
        # Find or create label
        label = existing_labels.get(label_name.lower())
        if not label:
            create_resp = await _google().api_request("post", f"{GMAIL_API}/labels", user_id, json={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            })
            label = create_resp.json()
            existing_labels[label_name.lower()] = label

        # Apply label to messages
        await _google().api_request("post", f"{GMAIL_API}/messages/batchModify", user_id, json={
            "ids": msg_ids,
            "addLabelIds": [label["id"]],
        })
        results.append(f"📁 {label_name}: {len(msg_ids)} email(s)")

    summary = "\n".join(results)
    return f"Organizei {len(categories)} emails em {len(label_groups)} pastas:\n{summary}"


# ===== Gmail Filters =====

@tool_action(
    name="create_gmail_filter",
    description="Create a Gmail filter that automatically applies a label to incoming emails matching criteria (from, to, subject, has words, etc).",
    integration="google",
    params={
        "from_address": {"type": "string", "description": "Filter emails FROM this address (optional)"},
        "to_address": {"type": "string", "description": "Filter emails TO this address (optional)"},
        "subject": {"type": "string", "description": "Filter by subject contains (optional)"},
        "query": {"type": "string", "description": "Gmail search query for advanced matching (optional)"},
        "label_name": {"type": "string", "description": "Label to apply (will create if not exists)"},
        "archive": {"type": "boolean", "description": "Skip inbox (archive) matching emails (default: false)"},
    },
)
async def create_gmail_filter(user_id: str, label_name: str, from_address: str = "", to_address: str = "",
                               subject: str = "", query: str = "", archive: bool = False) -> str:
    # Find or create the label
    labels_resp = await _google().api_request("get", f"{GMAIL_API}/labels", user_id)
    labels = labels_resp.json().get("labels", [])
    target = next((l for l in labels if l["name"].lower() == label_name.lower()), None)

    if not target:
        create_resp = await _google().api_request("post", f"{GMAIL_API}/labels", user_id, json={
            "name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show",
        })
        target = create_resp.json()

    # Build filter criteria
    criteria = {}
    if from_address:
        criteria["from"] = from_address
    if to_address:
        criteria["to"] = to_address
    if subject:
        criteria["subject"] = subject
    if query:
        criteria["query"] = query

    if not criteria:
        return "Error: at least one filter criteria is required (from, to, subject, or query)"

    # Build actions
    action = {"addLabelIds": [target["id"]]}
    if archive:
        action["removeLabelIds"] = ["INBOX"]

    # Create filter
    resp = await _google().api_request("post", f"{GMAIL_API}/settings/filters", user_id, json={
        "criteria": criteria,
        "action": action,
    })
    filter_data = resp.json()
    return f"Filtro criado (ID: {filter_data.get('id', '?')}): emails {criteria} → label '{label_name}'" + (" (arquivar)" if archive else "")


@tool_action(
    name="list_gmail_filters",
    description="List all Gmail filters configured for the user.",
    integration="google",
    params={},
)
async def list_gmail_filters(user_id: str) -> str:
    resp = await _google().api_request("get", f"{GMAIL_API}/settings/filters", user_id)
    filters = resp.json().get("filter", [])
    if not filters:
        return "Nenhum filtro configurado"

    # Get labels for name resolution
    labels_resp = await _google().api_request("get", f"{GMAIL_API}/labels", user_id)
    label_map = {l["id"]: l["name"] for l in labels_resp.json().get("labels", [])}

    lines = []
    for f in filters:
        criteria = f.get("criteria", {})
        action = f.get("action", {})
        criteria_parts = []
        if "from" in criteria: criteria_parts.append(f"from:{criteria['from']}")
        if "to" in criteria: criteria_parts.append(f"to:{criteria['to']}")
        if "subject" in criteria: criteria_parts.append(f"subject:{criteria['subject']}")
        if "query" in criteria: criteria_parts.append(f"query:{criteria['query']}")

        labels = [label_map.get(lid, lid) for lid in action.get("addLabelIds", [])]
        lines.append(f"- {' '.join(criteria_parts)} → {', '.join(labels)}")

    return "\n".join(lines)
