from fastapi import APIRouter
from app.api import auth, chat, integrations, automations, setup

router = APIRouter()
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(integrations.router)
router.include_router(automations.router)
router.include_router(setup.router)
