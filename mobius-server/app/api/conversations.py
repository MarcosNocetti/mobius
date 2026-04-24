"""Conversations API — list, get, continue conversations."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from jose import JWTError
from app.core.database import get_session
from app.core.security import decode_token
from app.models.conversation import Conversation, Message

router = APIRouter(prefix="/conversations", tags=["conversations"])
bearer = HTTPBearer()


async def _get_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        return decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    tool_name: str | None = None
    tool_args: str | None = None
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    message_count: int
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
    offset: int = 0,
):
    """List conversations for the current user, most recent first."""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
        .offset(offset)
    )
    convs = result.scalars().all()
    return [
        ConversationSummary(
            id=c.id, title=c.title, message_count=c.message_count,
            created_at=c.created_at, updated_at=c.updated_at,
        )
        for c in convs
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a conversation with all its messages."""
    conv = await session.get(Conversation, conversation_id)
    if not conv or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs_result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()

    return ConversationDetail(
        id=conv.id, title=conv.title, message_count=conv.message_count,
        messages=[
            MessageResponse(
                id=m.id, role=m.role, content=m.content,
                tool_name=m.tool_name, tool_args=m.tool_args,
                created_at=m.created_at,
            )
            for m in messages
        ],
        created_at=conv.created_at, updated_at=conv.updated_at,
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a conversation and all its messages."""
    conv = await session.get(Conversation, conversation_id)
    if not conv or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete messages first
    msgs = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id)
    )
    for msg in msgs.scalars().all():
        await session.delete(msg)
    await session.delete(conv)
    await session.commit()


@router.get("/admin/all", response_model=list[ConversationDetail])
async def admin_all_conversations(
    session: AsyncSession = Depends(get_session),
    limit: int = 100,
):
    """Admin endpoint — get ALL conversations with messages for analysis.
    No auth required for dev/analysis purposes."""
    result = await session.execute(
        select(Conversation).order_by(desc(Conversation.updated_at)).limit(limit)
    )
    convs = result.scalars().all()

    details = []
    for conv in convs:
        msgs_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
        messages = msgs_result.scalars().all()
        details.append(ConversationDetail(
            id=conv.id, title=conv.title, message_count=conv.message_count,
            messages=[
                MessageResponse(
                    id=m.id, role=m.role, content=m.content,
                    tool_name=m.tool_name, tool_args=m.tool_args,
                    created_at=m.created_at,
                )
                for m in messages
            ],
            created_at=conv.created_at, updated_at=conv.updated_at,
        ))
    return details
