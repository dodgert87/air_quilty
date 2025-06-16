from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.utils.exceptions_base import AppException
from app.domain.auth_logic import validate_token_and_get_user
from app.models.DB_tables.user import RoleEnum
from app.utils.config import settings

base = settings.API_VERSION

# Map endpoints to allowed roles
PATH_ROLE_MAP = {
    f"/api/{base}/auth/admin": [RoleEnum.admin],
    f"/api/{base}/auth/developer": [RoleEnum.admin, RoleEnum.developer],
    f"/api/{base}/auth/authenticated": [
        RoleEnum.admin,
        RoleEnum.developer,
        RoleEnum.authenticated,
    ],
}

class LoginAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Enforce HTTPS unless in local environment
        if request.url.scheme != "https" and settings.ENV != "local":
            return JSONResponse(
                status_code=403,
                content={"detail": "HTTPS is required"}
            )

        # Try to extract and validate JWT token
        auth_header = request.headers.get("Authorization")
        user = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                user = await validate_token_and_get_user(token)
                request.state.user = user
                request.state.user_id = user.id

            except AppException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"error": "Invalid or missing authentication."}
                )
            except ValueError as e:
                return JSONResponse(status_code=401, content={"detail": str(e)})
        else:
            request.state.user = None

        # Enforce role if endpoint is protected
        for prefix, allowed_roles in PATH_ROLE_MAP.items():
            if path.startswith(prefix):
                if user is None:
                    return JSONResponse(status_code=401, content={"detail": "Authentication required"})
                if user.role not in allowed_roles:
                    return JSONResponse(status_code=403, content={"detail": f"Access denied for role: {user.role}"})
                break

        return await call_next(request)
