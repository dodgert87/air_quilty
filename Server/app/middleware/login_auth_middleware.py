from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from uuid import UUID

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

        # Enforce HTTPS unless in local environment
        if request.url.scheme != "https" and settings.ENV != "local":
            return JSONResponse(
                status_code=403,
                content={"detail": "HTTPS is required"}
            )

        auth_header = request.headers.get("Authorization")
        user = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()

            # Try from cache first
            user = LoginAuthProcessor.get(token)

            if user is None:
                try:
                    # Step 1: Decode unverified token to extract user_id
                    payload_unverified = decode_jwt_unverified(token)
                    user_id = UUID(payload_unverified.get("sub", ""))

                    # Step 2: Fetch "login" secret for that user
                    async with run_in_transaction() as session:
                        login_secret = await get_user_secret_by_label(session, user_id, label="login")
                        if not login_secret or not login_secret.is_active:
                            raise AuthValidationError("Login secret not found or inactive")

                    # Step 3: Use decrypted secret to verify JWT
                    decode_jwt(token, secret=decrypt_secret(login_secret.secret))

                    # Step 4: Fetch and cache user
                    user = await get_user_by_id(session, user_id)
                    if not user:
                        raise AuthValidationError("User not found")

                    LoginAuthProcessor.add(token, user)

                except AppException as e:
                    return JSONResponse(
                        status_code=e.status_code,
                        content={"error": "Invalid or missing authentication."}
                    )
                except Exception as e:
                    return JSONResponse(status_code=401, content={"detail": f"Token error: {str(e)}"})

            request.state.user = user
            request.state.user_id = user.id if user else None
        else:
            request.state.user = None

        # Role-based access enforcement
        for prefix, allowed_roles in PATH_ROLE_MAP.items():
            if path.startswith(prefix):
                if user is None:
                    return JSONResponse(status_code=401, content={"detail": "Authentication required"})
                if user.role not in allowed_roles:
                    return JSONResponse(status_code=403, content={"detail": f"Access denied for role: {user.role}"})
                break

        return await call_next(request)
