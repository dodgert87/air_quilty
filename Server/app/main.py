import asyncio
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from starlette.middleware import Middleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.domain.mqtt_listener import mqtt_state

from sqlalchemy import text
from slowapi.errors import RateLimitExceeded


from app.domain.api_key_processor import APIKeyAuthProcessor
from app.exception_handlers import app_exception_handler, fallback_exception_handler, validation_error_handler
from app.utils.exceptions_base import AppException

from app.middleware.login_auth_middleware import LoginAuthMiddleware
from app.middleware.api_key_auth_middleware import APIKeyAuthMiddleware
from app.middleware.rate_limit_middleware import limiter, rate_limit_exceeded_handler
from app.middleware.enforce_https_middleware import EnforceHTTPSMiddleware

from app.utils.config import settings
from app.infrastructure.database.init_db import init_db
from app.infrastructure.database.session import engine
from app.api.rest.router import router as rest_router
from app.api.graphql.router import router as graphql_router
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
    Middleware(ProxyHeadersMiddleware,  # type: ignore[arg-type]
               trusted_hosts=["tamkairquality.duckdns.org"]),
    Middleware(EnforceHTTPSMiddleware),
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
versioned_router.include_router(graphql_router)
app.include_router(versioned_router)

# ─── Custom Exception Handlers ───────────────────────────────
app.add_exception_handler(AppException, app_exception_handler) # type: ignore
app.add_exception_handler(RequestValidationError, validation_error_handler) # type: ignore
app.add_exception_handler(Exception, fallback_exception_handler) # type: ignore


# ────────────────────────────────────────────────────────
# ASCII banner (TAMK Air Quality API)
# ────────────────────────────────────────────────────────
ASCII_BANNER = r"""

████████╗ █████╗ ███╗   ███╗██╗  ██╗     █████╗ ██╗██████╗      ██████╗ ██╗   ██╗ █████╗ ██╗     ██╗████████╗██╗   ██╗     █████╗ ██████╗ ██╗
╚══██╔══╝██╔══██╗████╗ ████║██║ ██╔╝    ██╔══██╗██║██╔══██╗    ██╔═══██╗██║   ██║██╔══██╗██║     ██║╚══██╔══╝╚██╗ ██╔╝    ██╔══██╗██╔══██╗██║
   ██║   ███████║██╔████╔██║█████╔╝     ███████║██║██████╔╝    ██║   ██║██║   ██║███████║██║     ██║   ██║    ╚████╔╝     ███████║██████╔╝██║
   ██║   ██╔══██║██║╚██╔╝██║██╔═██╗     ██╔══██║██║██╔══██╗    ██║▄▄ ██║██║   ██║██╔══██║██║     ██║   ██║     ╚██╔╝      ██╔══██║██╔═══╝ ██║
   ██║   ██║  ██║██║ ╚═╝ ██║██║  ██╗    ██║  ██║██║██║  ██║    ╚██████╔╝╚██████╔╝██║  ██║███████╗██║   ██║      ██║       ██║  ██║██║     ██║
   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝     ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝      ╚═╝       ╚═╝  ╚═╝╚═╝     ╚═╝


"""

ABOUT = (
    f"\nTAMK Air Quality API – backend service\n"
    f"Version   : {getattr(settings, 'VERSION', 'development')}\n\n"
    f"REST docs   : /docs\n"
    f"Dash board   : /dashboard/page1\n"
    f"Project docs: GitLab Wiki (https://gitlab.tamk.cloud/tamk-projects/summer-projects/2025/036-a3-air-quality.git)\n"
    f"Send a bug report: abdenour.abdelaziz@tuni.fi\n"
    f"{'-'*55}\n"
)


# ────────────────────────────────────────────────────────
# Unified landing page  +  health details (plain-text)
# ────────────────────────────────────────────────────────
limiter.shared_limit("300/minute", scope="landing")
@app.get("/", response_class=PlainTextResponse, tags=["Misc"])
async def landing_and_health() -> PlainTextResponse:
    """
    ASCII landing banner **plus** live health information for DB and MQTT listener,
    returned as plain text for quick human inspection.
    """
    # ---------- Database check ----------
    db_status_line = "unknown"
    db_detail = ""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status_line = "ok"
    except Exception as exc:
        db_status_line = "error"
        db_detail = f" ({exc})"
        logger.warning("[HEALTH] DB check failed: %s", exc)

    # ---------- MQTT status ----------
    mqtt_status_text = "running" if mqtt_state.is_running else "not running"
    mqtt_last_msg   = (
        mqtt_state.last_message_at.isoformat() if mqtt_state.last_message_at else "—"
    )
    mqtt_last_dev   = (
        str(mqtt_state.last_device_id) if mqtt_state.last_device_id else "—"
    )
    mqtt_msg_count  = mqtt_state.message_count

    # ---------- Compose plain-text response ----------
    health_block = (
        "DATABASE  : " + db_status_line + db_detail + "\n"
        "MQTT      : " + mqtt_status_text + "\n"
        f"  last_message_at : {mqtt_last_msg}\n"
        f"  last_device_id  : {mqtt_last_dev}\n"
        f"  message_count   : {mqtt_msg_count}\n"
    )

    response_text = ASCII_BANNER + ABOUT + health_block
    return PlainTextResponse(content=response_text, status_code=200 if db_status_line == "ok" else 503)





