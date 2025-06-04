from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException, status
from app.domain.auth_logic import validate_token_and_get_user
from app.utils.config import settings


class LoginAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Step 1: Block all HTTP traffic except sensor/latest
        if request.url.scheme != "https":
            if settings.ENV != "local" and not (
                request.method == "GET" and request.url.path == "/api/v1/sensor/latest"
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "HTTPS is required for all endpoints except /sensor/latest"}
                )

        # Step 2: Extract Bearer token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                user_context = await validate_token_and_get_user(token)
                request.state.user = user_context
            except ValueError as e:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": str(e)})
        else:
            request.state.user = None  # anonymous access

        return await call_next(request)
