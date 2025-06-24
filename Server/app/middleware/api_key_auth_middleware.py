from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from app.infrastructure.database.repository.restAPI.user_repository import get_user_by_id
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.exceptions_base import AuthValidationError
from app.utils.hashing import verify_value
from app.models.DB_tables.user import RoleEnum
from app.utils.config import settings

from app.domain.api_key_processor import APIKeyAuthProcessor

base = settings.API_VERSION

# Role access map
PATH_ROLE_MAP = {
    f"/api/{base}/sensor/admin": [RoleEnum.admin],
    f"/api/{base}/sensor/developer": [RoleEnum.admin, RoleEnum.developer],
    f"/api/{base}/sensor/authenticated": [
        RoleEnum.admin,
        RoleEnum.developer,
        RoleEnum.authenticated,
    ],
    f"/api/{base}/sensor": [
        RoleEnum.admin,
        RoleEnum.developer,
        RoleEnum.authenticated,
    ],
}


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith(f"/api/{settings.API_VERSION}/sensor"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(status_code=401, content={"detail": "Missing API key"})

        # Match key against preloaded registry
        try:
            user = None
            async with run_in_transaction() as session:
                for config in APIKeyAuthProcessor.get_all():
                    if verify_value(api_key, config.key.get_secret_value()):
                        user = await APIKeyAuthProcessor.match(api_key)
                        break

            if not user:
                raise AuthValidationError("Invalid or inactive API key")

            request.state.user = user
            request.state.user_id = user.id
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
