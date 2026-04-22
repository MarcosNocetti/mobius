import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError
from app.core.security import decode_token, decrypt_api_key
from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation, Message
from app.models.user import User as UserModel
from app.agents.engine import run_agent

router = APIRouter()


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, token: str = Query(...)):
    # Authenticate
    try:
        user_id = decode_token(token)
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # Load user from DB to get their API keys
    async with AsyncSessionLocal() as session:
        db_user = await session.get(UserModel, user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            user_message = payload.get("message", "")
            model = payload.get("model", "gemini/gemini-2.0-flash")

            # Persist conversation + user message
            async with AsyncSessionLocal() as session:
                conv = Conversation(user_id=user_id)
                session.add(conv)
                await session.flush()
                session.add(Message(conversation_id=conv.id, role="user", content=user_message))
                await session.commit()
                conv_id = conv.id

            # Resolve user API key for the requested provider
            provider = model.split("/")[0] if "/" in model else "gemini"
            user_key = None
            if db_user and db_user.api_keys and provider in db_user.api_keys:
                user_key = decrypt_api_key(db_user.api_keys[provider])

            # Stream LLM response
            full_response_parts = []

            async def send_token(chunk: str):
                full_response_parts.append(chunk)
                await websocket.send_text(json.dumps({"type": "token", "content": chunk}))

            await run_agent(
                message=user_message,
                model=model,
                api_key=user_key,
                tools=[],
                on_token=send_token,
            )

            # Persist assistant message
            async with AsyncSessionLocal() as session:
                session.add(Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content="".join(full_response_parts).strip()
                ))
                await session.commit()

            await websocket.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        pass
