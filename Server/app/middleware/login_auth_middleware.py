from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from uuid import UUID
from loguru import logger

from app.infrastructure.database.transaction import run_in_transaction
from app.utils.jwt_utils import decode_jwt_unverified, decode_jwt
from app.utils.exceptions_base import AppException, AuthValidationError
from app.models.DB_tables.user import RoleEnum
from app.utils.config import settings
from app.domain.login_auth_processor import LoginAuthProcessor
from app.infrastructure.database.repository.restAPI.user_repository import get_user_by_id
from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_label
from app.utils.crypto_utils import decrypt_secret

base = settings.API_VERSION

PATH_ROLE_MAP = {
    f"/api/{base}/auth/admin": [RoleEnum.admin],
    f"/api/{base}/auth/developer": [RoleEnum.admin, RoleEnum.developer],
    f"/api/{base}/auth/authenticated": [
        RoleEnum.admin,
        RoleEnum.developer,
        RoleEnum.authenticated,
    ],
    f"/api/{base}/auth/webhooks": [
        RoleEnum.admin,
        RoleEnum.developer,
        RoleEnum.authenticated,
    ],
}


class LoginAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Enforce HTTPS unless in dev
        if request.url.scheme != "https" and settings.ENV != "local":
            logger.warning(f"[LoginAuth] HTTPS enforcement triggered for path {path}")
            return JSONResponse(
                status_code=403,
                content={"detail": "HTTPS is required"}
            )

        auth_header = request.headers.get("Authorization")
        user = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            logger.debug(f"[LoginAuth] Bearer token received")

            user = LoginAuthProcessor.get(token)
            if user:
                logger.debug(f"[LoginAuth] Token hit in cache for user {user.id}")
            else:
                try:
                    logger.debug("[LoginAuth] Decoding JWT without verification to extract user ID")
                    unverified = decode_jwt_unverified(token)
                    user_id = UUID(unverified.get("sub", ""))

                    async with run_in_transaction() as session:
                        login_secret = await get_user_secret_by_label(session, user_id, label="login")
                        if not login_secret or not login_secret.is_active:
                            raise AuthValidationError("Login secret not found or inactive")

                        decode_jwt(token, secret=decrypt_secret(login_secret.secret))
                        user = await get_user_by_id(session, user_id)
                        if not user:
                            raise AuthValidationError("User not found")

                        LoginAuthProcessor.add(token, user)
                        logger.debug(f"[LoginAuth] Token validated and user {user.id} cached")

                except AppException as ae:
                    logger.warning(f"[LoginAuth] Auth exception: {ae.public_message}")
                    return JSONResponse(
                        status_code=ae.status_code,
                        content={"error": ae.public_message}
                    )
                except Exception as e:
                    logger.exception("[LoginAuth] Unexpected JWT error")
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Token validation failed"}
                    )

        request.state.user = user
        request.state.user_id = user.id if user else None

        # Role-based access check
        for prefix, allowed_roles in PATH_ROLE_MAP.items():
            if path.startswith(prefix):
                if user is None:
                    logger.warning(f"[LoginAuth] Access denied to unauthenticated user on {path}")
                    return JSONResponse(status_code=401, content={"detail": "Authentication required"})
                if user.role not in allowed_roles:
                    logger.warning(f"[LoginAuth] Access denied for user {user.id} with role {user.role}")
                    return JSONResponse(status_code=403, content={"detail": f"Access denied for role: {user.role}"})
                break

        return await call_next(request)
