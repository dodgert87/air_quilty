import time
import traceback
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.utils.exceptions_base import AppException
from app.models.DB_tables.rest_logs import LogDomain
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
from loguru import logger



async def app_exception_handler(request: Request, exc: AppException):
    try:
        domain = LogDomain(exc.domain)
    except ValueError:
        domain = LogDomain.OTHER

    # Log the internal error details (visible only to developers)
    logger.error(f"[{domain.value}] AppException: {exc.internal_message}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.public_message}
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    start_time = getattr(request.state, "start_time", time.time())

    logger.error(f"[VALIDATION] Request validation failed: {exc.errors()}")

    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Invalid request",
            "details": exc.errors()
        }
    )

async def fallback_exception_handler(request: Request, exc: Exception):
    start_time = getattr(request.state, "start_time", time.time())
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    logger.error(f"[UNHANDLED EXCEPTION] {str(exc)}\n{tb_str}")

    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )
