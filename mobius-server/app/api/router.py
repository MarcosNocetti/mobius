from fastapi import APIRouter
from app.api import auth, chat, automations, connect, conversations, web_chat

router = APIRouter()
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(automations.router)
router.include_router(connect.router)
router.include_router(connect.legacy_router)
router.include_router(conversations.router)
router.include_router(web_chat.router)
