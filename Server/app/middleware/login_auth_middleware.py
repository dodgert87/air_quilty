from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException, status
from app.domain.auth_logic import validate_token_and_get_user
from app.utils.config import settings



class LoginAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only handle specific paths
        if not path.startswith("/api/v1/auth") and not path.startswith("/api/v1/admin"):
            return await call_next(request)

        # Optional: HTTPS enforcement (skip in local)
        if request.url.scheme != "https" and settings.ENV != "local":
            return JSONResponse(
                status_code=403,
                content={"detail": "HTTPS is required"}
            )

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                user_context = await validate_token_and_get_user(token)
                request.state.user = user_context
            except ValueError as e:
                return JSONResponse(status_code=401, content={"detail": str(e)})
        else:
            request.state.user = None

        return await call_next(request)
