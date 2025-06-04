from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from app.domain.auth_logic import validate_api_key

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only handle /sensor
        if not path.startswith("/api/v1/sensor"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(status_code=401, content={"detail": "Missing API key"})

        try:
            user = await validate_api_key(api_key)
            request.state.user = user
            request.state.auth_method = "apikey"
        except Exception as e:
            return JSONResponse(status_code=401, content={"detail": f"API key auth failed: {str(e)}"})

        return await call_next(request)
