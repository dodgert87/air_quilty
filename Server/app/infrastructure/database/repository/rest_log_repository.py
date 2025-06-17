from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.models.DB_tables.rest_logs import RestLog, HTTPMethod, LogDomain
from typing import Optional
import uuid
from datetime import datetime, timezone


async def insert_rest_log(
    session: AsyncSession,
    *,
    method: HTTPMethod,
    endpoint: str,
    domain: LogDomain,
    user_id: Optional[uuid.UUID],
    ip_address: str,
    request_body: dict,
    response_status: int,
    response_time_ms: int,
    user_agent: str,
    error_message: Optional[str] = None,
    timestamp: Optional[datetime] = None
) -> None:
    """
    Insert a new REST log entry into the database.

    Args:
        session: SQLAlchemy async session.
        method: HTTP method used.
        endpoint: Path of the request.
        domain: Domain category (auth, sensor, etc).
        user_id: Optional user ID (from token).
        api_key: Optional API key label.
        ip_address: Request origin IP.
        query_params: Request query parameters (dict).
        request_body: Request payload.
        response_status: HTTP response code.
        response_time_ms: Time taken in ms.
        user_agent: Browser/client agent string.
        error_message: Optional error description.
        timestamp: Optional override for log time (UTC).
    """
    stmt = insert(RestLog).values(
        method=method,
        endpoint=endpoint,
        domain=domain,
        user_id=user_id,
        ip_address=ip_address,
        request_body=request_body,
        response_status=response_status,
        response_time_ms=response_time_ms,
        user_agent=user_agent,
        error_message=error_message,
        timestamp = timestamp or datetime.now(timezone.utc).replace(tzinfo=None)
    )

    await session.execute(stmt)
