import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError
from app.core.security import decode_token, decrypt_api_key
from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation, Message
from app.models.user import User as UserModel
from app.agents.engine import run_agent

logger = logging.getLogger("mobius.chat")

router = APIRouter()

_MODEL_MAP = {
    "gemini-flash": "gemini/gemini-2.0-flash",
    "claude-sonnet": "anthropic/claude-sonnet-4-6",
    "gpt-4o": "openai/gpt-4o",
}


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, token: str = Query(...)):
    # Authenticate
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

            logger.info(f"[ws] message={user_message!r} raw_model={raw_model!r} → model={model!r}")

            # Reload user each message to pick up freshly saved API keys
            async with AsyncSessionLocal() as session:
                db_user = await session.get(UserModel, user_id)

            # Resolve user API key
            provider = model.split("/")[0] if "/" in model else "gemini"
            user_key = None
            if db_user and db_user.api_keys:
                logger.info(f"[ws] stored providers: {list(db_user.api_keys.keys())}")
                if provider in db_user.api_keys:
                    user_key = decrypt_api_key(db_user.api_keys[provider])
                    logger.info(f"[ws] using user key for provider={provider!r}")
                else:
                    logger.info(f"[ws] no user key for provider={provider!r}, falling back to server key")
            else:
                logger.info(f"[ws] db_user has no api_keys, falling back to server key")

            # Persist conversation + user message
            async with AsyncSessionLocal() as session:
                conv = Conversation(user_id=user_id)
                session.add(conv)
                await session.flush()
                session.add(Message(conversation_id=conv.id, role="user", content=user_message))
                await session.commit()
                conv_id = conv.id

            # Stream LLM response
            full_response_parts = []

            async def send_token(chunk: str):
                full_response_parts.append(chunk)
                await websocket.send_text(json.dumps({"type": "token", "content": chunk}))

            logger.info(f"[ws] calling run_agent model={model!r} key={'user' if user_key else 'server'}")
            try:
                await run_agent(
                    message=user_message,
                    model=model,
                    api_key=user_key,
                    tools=[],
                    on_token=send_token,
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[ws] run_agent failed: {error_msg}")
                await websocket.send_text(json.dumps({"type": "error", "content": error_msg}))
                await websocket.send_text(json.dumps({"type": "done"}))
                continue

            # Persist assistant message
            async with AsyncSessionLocal() as session:
                session.add(Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content="".join(full_response_parts).strip()
                ))
                await session.commit()

            await websocket.send_text(json.dumps({"type": "done"}))
            logger.info(f"[ws] done, sent {len(full_response_parts)} chunks")

    except WebSocketDisconnect:
        logger.info(f"[ws] user_id={user_id} disconnected")
    except Exception as e:
        logger.error(f"[ws] unhandled error: {e}", exc_info=True)
