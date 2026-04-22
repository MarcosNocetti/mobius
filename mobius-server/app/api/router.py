from fastapi import APIRouter
from app.api import auth, chat
from app.api.integrations import router as integrations_router

router = APIRouter()
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(integrations_router)
