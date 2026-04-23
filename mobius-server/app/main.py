import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.api.router import router
from app.core.database import init_db, AsyncSessionLocal
from app.core.redis import redis_client
from app.agents.engine import run_agent
from app.models.automation import ScheduledAutomation

scheduler = AsyncIOScheduler()


async def run_automation(automation_id: str, prompt: str):
    """Run a scheduled automation with Redis lock to prevent duplicate execution."""
    lock_key = f"lock:automation:{automation_id}"
    acquired = await redis_client.set(lock_key, "1", nx=True, ex=300)
    if not acquired:
        return

    try:
        await run_agent(
            message=prompt,
            model="gemini/gemini-2.0-flash",
            api_key=None,
            tools=[],
            on_token=lambda t: None,
        )
        async with AsyncSessionLocal() as session:
            auto = await session.get(ScheduledAutomation, automation_id)
            if auto:
                auto.last_run = datetime.utcnow()
                await session.commit()
    finally:
        await redis_client.delete(lock_key)


async def load_automations():
    """Load all active automations from DB and schedule them."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScheduledAutomation).where(ScheduledAutomation.active == True)
        )
        automations = result.scalars().all()

    for auto in automations:
        try:
            trigger = CronTrigger.from_crontab(auto.cron_expr)
            scheduler.add_job(
                run_automation,
                trigger=trigger,
                args=[auto.id, auto.prompt],
                id=auto.id,
                replace_existing=True,
            )
        except Exception as e:
            print(f"Failed to schedule automation {auto.id}: {e}")


async def load_saved_credentials():
    """Load Google OAuth credentials saved via /setup from Redis."""
    try:
        cid = await redis_client.get("setup:google_client_id")
        csec = await redis_client.get("setup:google_client_secret")
        if cid and csec:
            from app.core.config import settings
            settings.GOOGLE_CLIENT_ID = cid
            settings.GOOGLE_CLIENT_SECRET = csec
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        await load_saved_credentials()
    except Exception:
        pass
    try:
        await load_automations()
    except Exception:
        pass  # Redis/DB may not be available in tests
    try:
        scheduler.start()
    except Exception:
        pass  # Scheduler may fail in test environments with closed event loops
    yield
    try:
        scheduler.shutdown()
    except Exception:
        pass


app = FastAPI(title="Mobius Server", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
