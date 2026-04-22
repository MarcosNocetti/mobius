from fastapi import APIRouter
from app.integrations.google import router as google_router

router = APIRouter()
router.include_router(google_router)
