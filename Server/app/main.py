import asyncio
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.middleware import Middleware
from sqlalchemy import text
from app.infrastructure.database.transaction import run_in_transaction
from app.constants.webhooks import WebhookEvent
from app.middleware.RestLoggerMiddleware import RestLoggerMiddleware
from app.exception_handlers import app_exception_handler, fallback_exception_handler, validation_error_handler
from app.utils.exceptions_base import AppException
from app.middleware.login_auth_middleware import LoginAuthMiddleware
from app.middleware.api_key_auth_middleware import APIKeyAuthMiddleware
from app.utils.config import settings
from app.infrastructure.database.init_db import init_db
from app.infrastructure.database.session import engine
from app.api.rest.router import router as rest_router
from app.api.graphql.router import graphql_router
from app.api.webhook.router import router as webhook_router
from app.domain.webhooks.dispatcher import dispatcher

from app.utils.logging_config import setup_logging
from app.domain.mqtt_listener import listen_to_mqtt




setup_logging() # Initialize logging configuration

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # ─── Load webhook registries ──────────────────────────────
    await dispatcher.load_all_registries()


    # ─── Start MQTT Listener ──────────────────────────────────
    task = asyncio.create_task(listen_to_mqtt())

    yield

    # ─── Shutdown Cleanup ─────────────────────────────────────
    task.cancel()



middleware = [
    Middleware(LoginAuthMiddleware),
    Middleware(APIKeyAuthMiddleware),
    Middleware(RestLoggerMiddleware)
]
api_prefix = f"/api/{settings.API_VERSION}"

app = FastAPI(title="Air Quality API", lifespan=lifespan, middleware=middleware)

versioned_router = APIRouter(prefix=api_prefix)
versioned_router.include_router(rest_router)
versioned_router.include_router(webhook_router)
versioned_router.include_router(graphql_router, prefix="/sensor/data/graphql")
app.include_router(versioned_router)


app.add_exception_handler(AppException, app_exception_handler) # type: ignore
app.add_exception_handler(RequestValidationError, validation_error_handler) # type: ignore
app.add_exception_handler(Exception, fallback_exception_handler)


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

