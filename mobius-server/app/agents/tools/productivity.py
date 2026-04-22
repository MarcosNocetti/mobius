from app.integrations.google import create_calendar_event as _create_event, send_gmail as _send_gmail


async def create_calendar_event_tool(user_id: str, title: str, start_dt: str, end_dt: str) -> str:
    """Create a Google Calendar event. Returns event ID."""
    result = await _create_event(user_id, title, start_dt, end_dt)
    return f"Event created: {result.get('id')} — {result.get('summary')}"


async def send_gmail_tool(user_id: str, to: str, subject: str, body: str) -> str:
    """Send an email via Gmail. Returns message ID."""
    result = await _send_gmail(user_id, to, subject, body)
    return f"Email sent: {result.get('id')}"
