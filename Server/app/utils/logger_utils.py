import time
import uuid
from typing import Optional
from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rest_logs import HTTPMethod, LogDomain
from app.infrastructure.database.rest_log_repository import insert_rest_log
from loguru import logger


async def log_rest(
    *,
    request: Request,
    response: Response,
    db_session: AsyncSession,
    domain: LogDomain,
    user_id: Optional[uuid.UUID],
    start_time: float,
    error_message: Optional[str] = None
) -> None:
    try:
        duration_ms = int((time.time() - start_time) * 1000)
        method = HTTPMethod(request.method.upper())
        client_ip = request.client.host if request.client else "unknown"

        try:
            body = await request.json()
        except Exception:
            body = {}

        try:
            query_params = dict(request.query_params)
        except Exception:
            query_params = {}

        user_agent = request.headers.get("user-agent", "unknown")

        #  Pretty log to console
        pretty_log_to_console(
            domain=domain,
            method=method,
            path=request.url.path,
            user_id=str(user_id) if user_id else None,
            status=response.status_code,
            duration_ms=duration_ms,
            error_msg=error_message
        )


        #  Persist to DB
        await insert_rest_log(
            session=db_session,
            method=method,
            endpoint=request.url.path,
            domain=domain,
            user_id=user_id,
            ip_address=client_ip,
            request_body=body,
            response_status=response.status_code,
            response_time_ms=duration_ms,
            user_agent=user_agent,
            error_message=error_message
        )

    except Exception as e:
        logger.exception("REST logging failed")


def pretty_log_to_console(
    *,
    domain,
    method,
    path,
    user_id,
    status,
    duration_ms,
    error_msg=None
):
    logger.info("\n <bold>REST Request Log</bold>")
    logger.info(f"├── <cyan>Domain</cyan>    : {domain.value}")
    logger.info(f"├── <cyan>Method</cyan>    : {method.value}")
    logger.info(f"├── <cyan>Endpoint</cyan>  : {path}")
    logger.info(f"├── <cyan>Status</cyan>    : {status}")
    logger.info(f"├── <cyan>Duration</cyan>  : {duration_ms} ms")
    logger.info(f"├── <cyan>User ID</cyan>   : {user_id}")
    logger.info(f"└── <cyan>Error</cyan>     : {error_msg or 'None'}")