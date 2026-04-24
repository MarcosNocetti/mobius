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
from app.models.automation import Automation

scheduler = AsyncIOScheduler()


async def run_automation(automation_id: str):
    """Run a scheduled automation with Redis lock to prevent duplicate execution."""
    lock_key = f"lock:automation:{automation_id}"
    acquired = await redis_client.set(lock_key, "1", nx=True, ex=300)
    if not acquired:
        return

    try:
        async with AsyncSessionLocal() as session:
            auto = await session.get(Automation, automation_id)
            if not auto:
                return

            from app.automation.sandbox import execute_script
            from app.automation.context import AutomationContext
            import traceback

            ctx = AutomationContext(user_id=auto.user_id, automation_id=automation_id)
            try:
                result = await execute_script(auto.script, ctx)
                auto.last_result = result
                auto.last_error = None
                auto.status = "active"
            except Exception as e:
                auto.last_error = traceback.format_exc()
                auto.last_result = None
                auto.status = "error"

            auto.last_run = datetime.utcnow()
            auto.run_count += 1
            await session.commit()
    finally:
        await redis_client.delete(lock_key)


async def load_automations():
    """Load all active automations from DB and schedule them."""
    import json
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Automation).where(Automation.status == "active")
        )
        automations = result.scalars().all()

    for auto in automations:
        try:
            config = json.loads(auto.trigger_config) if isinstance(auto.trigger_config, str) else auto.trigger_config
            cron_expr = config.get("cron")
            if not cron_expr:
                continue
            trigger = CronTrigger.from_crontab(cron_expr)
            scheduler.add_job(
                run_automation,
                trigger=trigger,
                args=[auto.id],
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
            settings.GOOGLE_CLIENT_ID = cid.decode() if isinstance(cid, bytes) else cid
            settings.GOOGLE_CLIENT_SECRET = csec.decode() if isinstance(csec, bytes) else csec
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        await load_saved_credentials()
    except Exception:
        pass
    # Discover all integrations and their tools
    from app.integrations.registry import integration_registry
    integration_registry.get_all()  # triggers _discover()
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


# Serve Flutter web app as static files (if built)
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    # Serve all Flutter static files under /app/
    app.mount("/app/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")
    app.mount("/app/canvaskit", StaticFiles(directory=_static_dir / "canvaskit"), name="canvaskit")
    app.mount("/app/icons", StaticFiles(directory=_static_dir / "icons"), name="icons")

    for fname in ["flutter.js", "flutter_bootstrap.js", "flutter_service_worker.js",
                   "main.dart.js", "manifest.json", "favicon.png"]:
        fpath = _static_dir / fname
        if fpath.exists():
            @app.get(f"/app/{fname}", include_in_schema=False)
            async def serve_file(path=fpath):
                return FileResponse(path)

    @app.get("/app/{path:path}", include_in_schema=False)
    async def flutter_app(path: str = ""):
        return FileResponse(_static_dir / "index.html")

    @app.get("/app", include_in_schema=False)
    async def flutter_app_root():
        return FileResponse(_static_dir / "index.html")
