import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError
from app.core.security import decode_token
from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation, Message

router = APIRouter()

MOCK_RESPONSE = "Hello from Mobius! I am your AI assistant ready to help."


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, token: str = Query(...)):
    # Authenticate
    try:
        user_id = decode_token(token)
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            user_message = payload.get("message", "")

            # Persist conversation + user message
            async with AsyncSessionLocal() as session:
                conv = Conversation(user_id=user_id)
                session.add(conv)
                await session.flush()
                session.add(Message(conversation_id=conv.id, role="user", content=user_message))
                await session.commit()
                conv_id = conv.id

            # Stream mock response word by word
            words = MOCK_RESPONSE.split()
            full_response = []
            for word in words:
                chunk = word + " "
                full_response.append(chunk)
                await websocket.send_text(json.dumps({"type": "token", "content": chunk}))
                await asyncio.sleep(0.05)

            # Persist assistant message
            async with AsyncSessionLocal() as session:
                session.add(Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content="".join(full_response).strip()
                ))
                await session.commit()

            await websocket.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        pass
