from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from sqlalchemy import text
from app.config import settings
from app.infrastructure.database.init_db import init_db
from app.infrastructure.database.session import engine
from app.api.rest.router import router as rest_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

versioned_router = APIRouter(prefix=f"/api/{settings.API_VERSION}")
versioned_router.include_router(rest_router)

app.include_router(versioned_router)

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
