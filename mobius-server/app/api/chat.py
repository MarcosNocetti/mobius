import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.core.redis import redis_client as _redis
from jose import JWTError
from app.core.config import settings
from app.core.security import decode_token, decrypt_api_key
from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation, Message
from app.models.user import User as UserModel
from app.agents.engine import run_agent_with_tools
from app.integrations.registry import integration_registry

logger = logging.getLogger("mobius.chat")

router = APIRouter()

_MODEL_MAP = {
    "gemini-flash": "gemini/gemini-2.5-flash",
    "claude-sonnet": "anthropic/claude-sonnet-4-6",
    "gpt-4o": "openai/gpt-4o",
}

SYSTEM_PROMPT_TEMPLATE = """You are Mobius, a powerful AI productivity assistant that EXECUTES real actions.
Current date/time: {now}
Timezone: America/Sao_Paulo (UTC-3)

PERSONALITY:
- You are confident and proactive. You DO things, you don't just describe them.
- Never say "I can't" or "my capabilities are limited". If you have the tools, USE them.
- If a tool fails, explain the error and suggest a fix — don't give up.

RULES:
1. ALWAYS USE TOOLS when the user asks to do something actionable. Never just describe what you would do.
2. For dates like "amanhã", "segunda", "próxima semana" — calculate the actual date from the current date above.
3. Use ISO 8601 with timezone (e.g. 2026-04-24T10:00:00-03:00) for all datetimes.
4. If the user asks for multiple actions, make multiple tool calls.
5. After executing actions, confirm exactly what you did with details.
6. Respond in the same language the user writes in.
7. For automations: when the user wants recurring tasks, use create_automation to generate a Python script. The script uses ctx.tools.* (same tools you have) and ctx.ai.ask() for AI reasoning.
8. If the user asks for something that requires a disconnected integration, tell them EXACTLY what to do: "Connect [service] by tapping this link: [url]". Be specific, not vague."""


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

    # Track active conversation for this WebSocket session
    active_conv_id = None

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            user_message = payload.get("message", "")
            raw_model = payload.get("model", "gemini/gemini-2.5-flash")
            model = _MODEL_MAP.get(raw_model, raw_model)
            req_conv_id = payload.get("conversation_id")  # Optional: continue existing

            logger.info(f"[ws] message={user_message!r} model={model!r} conv={req_conv_id or 'new'}")

            # Reload user for API keys
            async with AsyncSessionLocal() as session:
                db_user = await session.get(UserModel, user_id)

            # Resolve API key
            provider = model.split("/")[0] if "/" in model else "gemini"
            user_key = None
            if db_user and db_user.api_keys and provider in db_user.api_keys:
                user_key = decrypt_api_key(db_user.api_keys[provider])

            # Get or create conversation
            async with AsyncSessionLocal() as session:
                conv_id = req_conv_id or active_conv_id
                if conv_id:
                    conv = await session.get(Conversation, conv_id)
                    if not conv or conv.user_id != user_id:
                        conv = None
                        conv_id = None

                if not conv_id:
                    # Generate title from first message
                    title = user_message[:60] + ("..." if len(user_message) > 60 else "")
                    conv = Conversation(user_id=user_id, title=title)
                    session.add(conv)
                    await session.flush()
                    conv_id = conv.id

                # Save user message
                session.add(Message(conversation_id=conv_id, role="user", content=user_message))
                conv.message_count = (conv.message_count or 0) + 1
                conv.updated_at = datetime.utcnow()
                await session.commit()

            active_conv_id = conv_id

            # Send conversation_id to client so it can continue
            await websocket.send_text(json.dumps({
                "type": "conversation_id", "content": conv_id
            }))

            # Load conversation history for context
            history_messages = []
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select as sa_select
                msgs = await session.execute(
                    sa_select(Message)
                    .where(Message.conversation_id == conv_id)
                    .order_by(Message.created_at)
                )
                for m in msgs.scalars().all():
                    if m.role in ("user", "assistant"):
                        history_messages.append({"role": m.role, "content": m.content})

            # Build tools
            tool_registry = await integration_registry.get_tools_for_user(user_id)

            # Build system prompt with context
            google_connected = False
            try:
                google = integration_registry.get("google")
                google_connected = await google.is_connected(user_id)
            except Exception:
                pass

            full_response_parts = []

            async def send_token(chunk: str):
                full_response_parts.append(chunk)
                await websocket.send_text(json.dumps({"type": "token", "content": chunk}))

            try:
                base_url = settings.BASE_URL or "http://localhost:8000"

                # Build dynamic integration status
                integration_notes = []
                for integ in integration_registry.get_all():
                    connected = await integ.is_connected(user_id)
                    if connected:
                        integration_notes.append(f"✅ {integ.display_name}: CONNECTED")
                    else:
                        url = f"{base_url}/connect/{integ.name}?user_id={user_id}"
                        integration_notes.append(f"❌ {integ.display_name}: NOT connected → {url}")

                # List available tools dynamically
                tool_list = "\n".join(
                    f"- {name}: {t['schema']['function']['description']}"
                    for name, t in tool_registry.items()
                )

                system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                integrations_status = "\n".join(integration_notes)
                full_system = f"{system_prompt}\n\nYour available tools:\n{tool_list}\n\nIntegration status:\n{integrations_status}"

                # Build full message with conversation history
                if len(history_messages) > 1:
                    # Include history — last message is the current one, already in history
                    history_text = "\n".join(
                        f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
                        for m in history_messages[:-1]  # exclude current message
                    )
                    full_message = f"{full_system}\n\nConversation history:\n{history_text}\n\nUser: {user_message}"
                else:
                    full_message = f"{full_system}\n\nUser: {user_message}"

                await run_agent_with_tools(
                    message=full_message,
                    model=model,
                    api_key=user_key,
                    tool_registry=tool_registry,
                    on_token=send_token,
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[ws] agent error: {error_msg}")
                await websocket.send_text(json.dumps({"type": "error", "content": error_msg}))

            # Persist assistant response
            assistant_content = "".join(full_response_parts).strip()
            async with AsyncSessionLocal() as session:
                conv = await session.get(Conversation, conv_id)
                session.add(Message(
                    conversation_id=conv_id, role="assistant", content=assistant_content,
                ))
                conv.message_count = (conv.message_count or 0) + 1
                conv.updated_at = datetime.utcnow()
                await session.commit()

            await websocket.send_text(json.dumps({"type": "done"}))
            logger.info(f"[ws] done, conv={conv_id}, {len(full_response_parts)} chunks")

    except WebSocketDisconnect:
        logger.info(f"[ws] user_id={user_id} disconnected")
    except Exception as e:
        logger.error(f"[ws] unhandled error: {e}", exc_info=True)
