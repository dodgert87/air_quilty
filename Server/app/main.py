from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from infrastructure.database.init_db import init_db
from infrastructure.database.session import engine



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # Run DB table creation
    yield  # Let FastAPI run



app = FastAPI(lifespan=lifespan)

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
