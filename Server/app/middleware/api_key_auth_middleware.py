from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from loguru import logger

from app.infrastructure.database.repository.restAPI.user_repository import get_user_by_id
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.exceptions_base import AuthValidationError
from app.utils.hashing import verify_value
from app.models.DB_tables.user import RoleEnum
from app.utils.config import settings
from app.domain.api_key_processor import APIKeyAuthProcessor

# Define base API version path
base = settings.API_VERSION

# Define role-based access control (RBAC) for endpoint prefixes
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
    """
    Middleware that enforces API key authentication and role-based access control
    for specific sensor-related API routes.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip middleware for non-sensor routes
        if not path.startswith(f"/api/{settings.API_VERSION}/sensor"):
            return await call_next(request)

        # Extract API key from request header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            logger.warning("[APIKeyAuth] Missing X-API-Key header")
            return JSONResponse(status_code=401, content={"detail": "Missing API key"})

        try:
            logger.debug("[APIKeyAuth] Authenticating API key...")

            user = None

            # Match API key using loaded key cache
            async with run_in_transaction() as session:
                for config in APIKeyAuthProcessor.get_all():
                    if verify_value(api_key, config.key.get_secret_value()):
                        user = await APIKeyAuthProcessor.match(api_key)
                        break

            # No user matched means invalid or expired key
            if not user:
                logger.warning("[APIKeyAuth] No matching user found for provided API key")
                raise AuthValidationError("Invalid or inactive API key")

            # Attach authenticated user details to request state for downstream access
            request.state.user = user
            request.state.user_id = user.id
            request.state.auth_method = "apikey"

            logger.debug(f"[APIKeyAuth] Authenticated user {user.id} ({user.role})")

        except AuthValidationError as ae:
            logger.warning(f"[APIKeyAuth] Auth failed: {ae.public_message}")
            return JSONResponse(status_code=401, content={"detail": ae.public_message})

        except Exception as e:
            logger.exception("[APIKeyAuth] Unexpected error during auth")
            return JSONResponse(status_code=500, content={"detail": "Internal auth error"})

        # Enforce role-based access control (RBAC)
        for prefix, allowed_roles in PATH_ROLE_MAP.items():
            if path.startswith(prefix):
                if user.role not in allowed_roles:
                    logger.warning(f"[APIKeyAuth] Access denied: {user.role} not in {allowed_roles}")
                    return JSONResponse(status_code=403, content={"detail": "Access denied"})
                break  # Only check the first matching prefix

        # Proceed with request if authenticated and authorized
        return await call_next(request)
