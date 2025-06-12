import time
import traceback
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.utils.exceptions_base import AppException
from app.models.rest_logs import LogDomain
from app.utils.logger_utils import log_rest
from app.infrastructure.database.transaction import run_in_transaction
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR



async def app_exception_handler(request: Request, exc: AppException):
    # Optional: dynamically map str -> LogDomain Enum
    try:
        domain = LogDomain(exc.domain)
    except ValueError:
        domain = LogDomain.OTHER


    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.public_message}
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    start_time = getattr(request.state, "start_time", time.time())
    response = JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Invalid request",
            "details": exc.errors()
        }
    )
    request.state._log_error_msg = str(exc)
    return response


async def fallback_exception_handler(request: Request, exc: Exception):
    start_time = getattr(request.state, "start_time", time.time())

    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    response = JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )
    request.state._log_error_msg = tb_str


    return response