from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger
from app.utils.config import settings

class EnforceHTTPSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if proto != "https" and settings.ENV != "local":
            logger.warning("[HTTPSEnforce] Blocked non-HTTPS request to %s", request.url.path)
            return JSONResponse(status_code=403, content={"detail": "HTTPS is required"})
        return await call_next(request)
