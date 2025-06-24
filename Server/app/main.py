import asyncio
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.middleware import Middleware
from sqlalchemy import text
from slowapi.errors import RateLimitExceeded

from app.domain.api_key_processor import APIKeyAuthProcessor
from app.exception_handlers import app_exception_handler, fallback_exception_handler, validation_error_handler
from app.utils.exceptions_base import AppException

from app.middleware.login_auth_middleware import LoginAuthMiddleware
from app.middleware.api_key_auth_middleware import APIKeyAuthMiddleware
from app.middleware.rate_limit_middleware import limiter, rate_limit_exceeded_handler

from app.utils.config import settings
from app.infrastructure.database.init_db import init_db
from app.infrastructure.database.session import engine
from app.api.rest.router import router as rest_router
from app.api.graphql.router import graphql_router
from app.api.webhook.router import router as webhook_router
from app.domain.webhooks.dispatcher import dispatcher

from app.domain.logging.logging_config import setup_logger
from loguru import logger
from app.domain.mqtt_listener import listen_to_mqtt




# ─── Logging Setup ───────────────────────────────────────────
setup_logger()

# ─── App Lifespan Logic ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await dispatcher.load_all_registries()
    await APIKeyAuthProcessor.load()
    task = asyncio.create_task(listen_to_mqtt())
    yield
    task.cancel()

# ─── Middleware List ─────────────────────────────────────────
middleware = [
    Middleware(LoginAuthMiddleware),
    Middleware(APIKeyAuthMiddleware),
]

# ─── FastAPI App Init ────────────────────────────────────────
api_prefix = f"/api/{settings.API_VERSION}"
app = FastAPI(title="Air Quality API", lifespan=lifespan, middleware=middleware)

# Register slowapi rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler) # type: ignore

# ─── Routers ─────────────────────────────────────────────────
versioned_router = APIRouter(prefix=api_prefix)
versioned_router.include_router(rest_router)
versioned_router.include_router(webhook_router)
versioned_router.include_router(graphql_router, prefix="/sensor/data/graphql")
app.include_router(versioned_router)

# ─── Custom Exception Handlers ───────────────────────────────
app.add_exception_handler(AppException, app_exception_handler) # type: ignore
app.add_exception_handler(RequestValidationError, validation_error_handler) # type: ignore
app.add_exception_handler(Exception, fallback_exception_handler) # type: ignore

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

