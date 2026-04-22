from fastapi import APIRouter
from app.integrations.google import router as google_router
from app.integrations.twitter import router as twitter_router

router = APIRouter()
router.include_router(google_router)
router.include_router(twitter_router)
