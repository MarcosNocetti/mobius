from fastapi import APIRouter
from app.integrations.google import router as google_router
from app.integrations.twitter import router as twitter_router
from app.integrations.instagram import router as instagram_router
from app.integrations.notion import router as notion_router
from app.integrations.linkedin import router as linkedin_router

router = APIRouter()
router.include_router(google_router)
router.include_router(twitter_router)
router.include_router(instagram_router)
router.include_router(notion_router)
router.include_router(linkedin_router)
