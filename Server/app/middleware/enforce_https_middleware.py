from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger
from app.utils.config import settings

class EnforceHTTPSMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces HTTPS connections for all incoming requests,
    except when running in a local development environment.
    """

    async def dispatch(self, request, call_next):
        # Determine the request protocol from the "x-forwarded-proto" header
        # (used when behind a proxy) or fallback to request.url.scheme.
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)

        # Block any non-HTTPS request in non-local environments
        if proto != "https" and settings.ENV != "local":
            logger.warning("[HTTPSEnforce] Blocked non-HTTPS request to %s", request.url.path)
            return JSONResponse(status_code=403, content={"detail": "HTTPS is required"})

        # Allow the request to proceed
        return await call_next(request)
