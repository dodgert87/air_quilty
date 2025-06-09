from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from app.domain.auth_logic import validate_api_key
from app.utils.config import settings


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from app.domain.auth_logic import validate_api_key
from app.models.user import RoleEnum
from app.utils.config import settings

base = settings.API_VERSION

# Define path-to-role access map
PATH_ROLE_MAP = {
    f"/api/{base}/sensor/admin": [RoleEnum.admin],
    f"/api/{base}/sensor/developer": [RoleEnum.admin, RoleEnum.developer],
    f"/api/{base}/sensor/authenticated": [
        RoleEnum.admin,
        RoleEnum.developer,
        RoleEnum.authenticated,
    ],
    f"/api/{base}/sensor": [  # default fallback for any protected sensor route
        RoleEnum.admin,
        RoleEnum.developer,
        RoleEnum.authenticated,
    ],
}

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only handle /sensor routes
        if not path.startswith(f"/api/{settings.API_VERSION}/sensor"):
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

        # Enforce RBAC
        for prefix, allowed_roles in PATH_ROLE_MAP.items():
            if path.startswith(prefix):
                if user.role not in allowed_roles:
                    return JSONResponse(status_code=403, content={"detail": "Access denied"})
                break

        return await call_next(request)