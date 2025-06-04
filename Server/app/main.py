from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from sqlalchemy import text
from app.models.sensor import SensorDataOut
from app.domain.sensor_logic import get_latest_sensor_data
from app.middleware.login_auth_middleware import LoginAuthMiddleware
from app.middleware.api_key_auth_middleware import APIKeyAuthMiddleware
from app.utils.config import settings
from app.infrastructure.database.init_db import init_db
from app.infrastructure.database.session import engine
from app.api.rest.router import router as rest_router
from app.models.response import Response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


middleware = [
    Middleware(LoginAuthMiddleware),
    Middleware(APIKeyAuthMiddleware)
]

app = FastAPI(lifespan=lifespan, middleware=middleware)

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

@app.get("/openData", response_model=Response.success[list[SensorDataOut]])
async def fetch_latest_sensor_data():
    try:
        data = await get_latest_sensor_data()
        return Response.success(
            message=Response.message.OK,
            http_code=Response.http.OK,
            app_code=Response.code.OK,
            data=data
        )
    except Exception as e:
        return JSONResponse(
            status_code=Response.http.SERVER_ERROR,
            content=Response.error(
                message=Response.message.UNKNOWN_ERROR,
                http_code=Response.http.SERVER_ERROR,
                app_code=Response.code.UNKNOWN_ERROR,
                errors={"error": str(e)}
            ).model_dump()
        )