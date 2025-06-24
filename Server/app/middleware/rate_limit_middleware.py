from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from starlette.responses import JSONResponse
from typing import Optional
from loguru import logger


def get_user_or_ip_key(request: Request) -> str:
    """
    Extract the rate-limiting key for a given request.
    - Use user_id if present (from auth middlewares).
    - Fallback to client IP.
    - Fallback to 'unknown' if client info is missing.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)

    client = request.client
    if client and client.host:
        return client.host

    return "unknown"


# ─── Create Limiter ──────────────────────────────────────────
limiter = Limiter(key_func=get_user_or_ip_key)


# ─── Custom 429 Error Handler ────────────────────────────────
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Return a 429 response with Retry-After header and structured error.
    """
    try:
        retry_after = int(getattr(exc, "headers", {}).get("Retry-After", 60))
    except Exception:
        retry_after = 60

    limit_key = get_user_or_ip_key(request)

    logger.warning(f"[RateLimit] Limit exceeded for key: {limit_key} | Retry after: {retry_after}s")

    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded. Please try again in {retry_after} seconds.",
            "error_code": "RATE_LIMIT",
            "limit_key": limit_key
        },
        headers={"Retry-After": str(retry_after)}
    )
