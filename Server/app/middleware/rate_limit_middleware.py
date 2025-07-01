from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from starlette.responses import JSONResponse
from typing import Optional
from loguru import logger


def get_user_or_ip_key(request: Request) -> str:
    """
    Extracts a key used for rate limiting.
    Priority:
    1. Authenticated user's ID (if available via middleware).
    2. Client IP address.
    3. Fallback to 'unknown' if neither is present.

    This allows per-user limits when logged in, and IP-based limits otherwise.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)

    client = request.client
    if client and client.host:
        return client.host

    return "unknown"


# ─────────────────────────────────────────────────────────────
# Create the rate limiter instance with a custom key extractor.
# This limiter can be used via decorators like @limiter.limit()
# or in route configuration with dependency injection.
# ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_user_or_ip_key)


# ─────────────────────────────────────────────────────────────
# Custom exception handler for RateLimitExceeded exceptions.
# Returns a 429 Too Many Requests response with:
# - Retry-After header (defaults to 60 seconds if unknown)
# - JSON error body with key info and retry time
# ─────────────────────────────────────────────────────────────
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom 429 error handler for rate limit violations.

    Includes Retry-After header and structured JSON response.
    Logs the offending key and retry duration.
    """
    try:
        # Get retry time from headers if present
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
