from fastapi import APIRouter
from app.api import auth, chat, automations, connect

router = APIRouter()
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(automations.router)
router.include_router(connect.router)
router.include_router(connect.legacy_router)
