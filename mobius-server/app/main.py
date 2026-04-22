from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Mobius Server", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
