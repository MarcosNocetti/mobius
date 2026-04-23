import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.core.redis import redis_client as _redis
from jose import JWTError
from app.core.security import decode_token, decrypt_api_key
from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation, Message
from app.models.user import User as UserModel
from app.agents.engine import run_agent_with_tools
from app.agents.tools.registry import get_tools_for_user

logger = logging.getLogger("mobius.chat")

router = APIRouter()

_MODEL_MAP = {
    "gemini-flash": "gemini/gemini-2.0-flash",
    "claude-sonnet": "anthropic/claude-sonnet-4-6",
    "gpt-4o": "openai/gpt-4o",
}

SYSTEM_PROMPT_TEMPLATE = """You are Mobius, a personal AI productivity assistant.
Current date/time: {now}
Timezone: America/Sao_Paulo (UTC-3)

You can perform real actions for the user using your available tools:
- create_calendar_event: Add events to Google Calendar
- send_gmail: Send emails via Gmail
- post_tweet: Post tweets on Twitter/X
- create_notion_page: Create pages in Notion

IMPORTANT RULES:
1. When the user asks to schedule, create events, send emails, or post — ALWAYS USE THE TOOLS immediately. Never just describe what you would do.
2. For dates like "amanhã", "segunda", "próxima semana" — calculate the actual date using the current date above.
3. Use ISO 8601 with timezone for datetimes (e.g. 2026-04-24T10:00:00-03:00).
4. If the user gives multiple events, create ALL of them with separate tool calls.
5. After executing, confirm exactly what you did.
6. Respond in the same language the user writes in."""


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, token: str = Query(...)):
    try:
        user_id = decode_token(token)
        logger.info(f"[ws] user_id={user_id} connected")
    except JWTError as e:
        logger.warning(f"[ws] auth failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            user_message = payload.get("message", "")
            raw_model = payload.get("model", "gemini/gemini-2.0-flash")
            model = _MODEL_MAP.get(raw_model, raw_model)

            logger.info(f"[ws] message={user_message!r} model={model!r}")

            # Reload user each message to pick up fresh API keys
            async with AsyncSessionLocal() as session:
                db_user = await session.get(UserModel, user_id)

            # Resolve API key
            provider = model.split("/")[0] if "/" in model else "gemini"
            user_key = None
            if db_user and db_user.api_keys and provider in db_user.api_keys:
                user_key = decrypt_api_key(db_user.api_keys[provider])
                logger.info(f"[ws] using user key for provider={provider!r}")

            # Persist user message
            async with AsyncSessionLocal() as session:
                conv = Conversation(user_id=user_id)
                session.add(conv)
                await session.flush()
                session.add(Message(conversation_id=conv.id, role="user", content=user_message))
                await session.commit()
                conv_id = conv.id

            # Check Google connection status
            google_connected = False
            try:
                google_raw = await _redis.get(f"oauth:google:{user_id}")
                google_connected = bool(google_raw)
            except Exception:
                pass

            # Build tools — only include Google tools if connected
            tool_registry = get_tools_for_user(user_id)
            if not google_connected:
                tool_registry = {k: v for k, v in tool_registry.items()
                                 if k not in ("create_calendar_event", "send_gmail")}

            # Stream response
            full_response_parts = []

            async def send_token(chunk: str):
                full_response_parts.append(chunk)
                await websocket.send_text(json.dumps({"type": "token", "content": chunk}))

            try:
                base_url = settings.BASE_URL or "http://localhost:8000"
                connect_url = f"{base_url}/connect/google?user_id={user_id}"
                google_note = (
                    "Google Calendar and Gmail are CONNECTED and ready to use."
                    if google_connected
                    else f"Google is NOT connected. If the user asks for calendar/email actions, "
                         f"tell them to connect first by opening this link: {connect_url}"
                )
                system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                full_system = f"{system_prompt}\n\nGoogle status: {google_note}"
                await run_agent_with_tools(
                    message=f"{full_system}\n\nUser: {user_message}",
                    model=model,
                    api_key=user_key,
                    tool_registry=tool_registry,
                    on_token=send_token,
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[ws] agent error: {error_msg}")
                await websocket.send_text(json.dumps({"type": "error", "content": error_msg}))

            # Persist assistant message
            async with AsyncSessionLocal() as session:
                session.add(Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content="".join(full_response_parts).strip(),
                ))
                await session.commit()

            await websocket.send_text(json.dumps({"type": "done"}))
            logger.info(f"[ws] done, {len(full_response_parts)} chunks")

    except WebSocketDisconnect:
        logger.info(f"[ws] user_id={user_id} disconnected")
    except Exception as e:
        logger.error(f"[ws] unhandled error: {e}", exc_info=True)
