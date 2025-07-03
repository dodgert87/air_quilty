from fastapi import APIRouter, Request, status
from typing import List

from loguru import logger
from pydantic import SecretStr
from app.domain.api_key_processor import APIKeyAuthProcessor
from app.utils.config import settings
from app.middleware.rate_limit_middleware import limiter
from app.models.schemas.rest.auth_schemas import (
    APIKeyConfig, APIKeyDeleteRequest, APIKeyRequest, ChangePasswordRequest, LoginRequest,
    LoginResponse, OnboardResult, SecretCreateRequest, SecretCreateResponse,
    SecretInfo, SecretLabelPayload, SecretLabelQuery, SecretTogglePayload,
    UserLookupPayload, UserOnboardRequest, UserResponse
)
from app.domain.auth_logic import (
    change_user_password, create_secret_for_user, delete_api_key_for_user, delete_secret_by_label,
    delete_user_by_identifier, find_user_info, generate_api_key_for_user,
    get_all_users, get_secret_info_for_user, get_user_profile_data,
    login_user, onboard_users_from_inputs, set_secret_active_status
)
from app.utils.exceptions_base import AppException, AuthValidationError

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ────────────────────────────────────────────────────────
# LOGIN ENDPOINT
# ────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Login and receive a JWT access token",
    description=f"""
Authenticate using your registered email and password.
Returns a signed JWT token with role, expiration, and token type.
The token should be used in subsequent requests via the `Authorization` header as `Bearer <token>`.

This endpoint:
- Does NOT require authentication to access.
- Is protected by rate limiting  {settings.LOGIN_RATE_LIMIT}.
- Returns a `401` on incorrect credentials.
"""
)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(request: Request, payload: LoginRequest):
    """
    Perform login and return an access token for authenticated usage.

    Payload:
        - email: Email address used during onboarding
        - password: Password (plain text)

    Returns:
        - access_token: JWT string
        - token_type: "bearer"
        - expires_in: Duration in seconds
    """
    try:
        response = await login_user(payload.email, payload.password)
        logger.info("[AUTH] Login successful | email=%s", payload.email)
        return response

    except AppException as ae:
        # Let custom AppExceptions (e.g., AuthValidationError) through as-is
        logger.warning("[AUTH] %s | email=%s", ae.message, payload.email)
        raise ae

    except Exception as e:
        # Unexpected error — log and return generic error
        logger.exception("[AUTH] Unexpected error during login | email=%s", payload.email)
        raise AppException.from_internal_error("Login failed", domain="auth")

# ────────────────────────────────────────────────────────
# PASSWORD CHANGE ENDPOINT
# ────────────────────────────────────────────────────────

@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Change user password",
    description=f"""
Allows an authenticated user to change their password.
This will also revoke all issued secrets and invalidate associated API keys.

Requirements:
- JWT token must be provided in the `Authorization: Bearer <token>` header.
- Payload must include the current password and new password.

Rate limited {settings.AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def change_password(payload: ChangePasswordRequest, request: Request):
    """
    Change the currently authenticated user's password.

    Payload:
        - old_password: current password
        - new_password: new desired password

    Side Effects:
        - Login secret is rotated
        - All cached API keys are invalidated

    Returns:
        - message confirming update
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        await change_user_password(user, payload.old_password, payload.new_password)
        APIKeyAuthProcessor.invalidate_user(user.id)
        logger.info("[AUTH] Password changed | user=%s", user.id)
        return {"message": "Password updated successfully"}

    except AppException as ae:
        logger.warning("[AUTH] %s | user=%s", ae.message, user.id)
        raise ae

    except Exception as e:
        logger.exception("[AUTH] Unexpected error during password change | user=%s", user.id)
        raise AppException.from_internal_error("Failed to change password", domain="auth")


# ────────────────────────────────────────────────────────
# TEST AUTHENTICATION ENDPOINT
# ────────────────────────────────────────────────────────

@router.get(
    "/test-auth",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Check if a user is authenticated",
    description=f"""
Returns information about the current authentication status.
This endpoint is useful for debugging or inspecting who is logged in.

- If no valid JWT is present, it reports guest access.
- If a valid JWT is present, it returns user metadata (id, role, email).

Rate limited {settings.AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def test_auth(request: Request):
    try:
        user = getattr(request.state, "user", None)
        if user is None:
            logger.info("[AUTH] Guest access verified")
            return {"message": "No user authenticated (guest access)"}

        logger.info("[AUTH] Authenticated check passed | user=%s", user.id)
        return {
            "message": "Authenticated user",
            "user_id": str(user.id),
            "role": user.role,
            "email": user.email
        }
    except AppException as ae:
        logger.warning("[AUTH] %s", ae.message)
        raise ae
    except Exception:
        logger.exception("[AUTH] Failed during auth test")
        raise AppException.from_internal_error("Failed to verify authentication", domain="auth")


# ────────────────────────────────────────────────────────
# ADMIN ENDPOINTS
# ────────────────────────────────────────────────────────

@router.post(
    "/admin/onboard-users",
    response_model=OnboardResult,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Onboard new users in bulk (Admin only)",
    description=f"""
Allows an admin to create multiple user accounts in a single request.
Each user will be initialized with a default password (from environment settings).
No email notifications are sent. This endpoint is rate-limited.

Authentication:
- Requires a valid JWT token with `admin` role.
- Enforced via `request.state.user.role`
- Rate limited by {settings.ADMIN_AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def onboard_users(request: Request, payload: UserOnboardRequest):
    try:
        result = await onboard_users_from_inputs(payload.users)
        logger.info("[ADMIN] Onboarded users | count=%d", len(payload.users))
        return result
    except AppException as ae:
        logger.warning("[ADMIN] %s | payload=%s", ae.message, payload)
        raise ae
    except Exception:
        logger.exception("[ADMIN] Failed to onboard users | payload=%s", payload)
        raise AppException.from_internal_error("Failed to onboard users", domain="auth")


@router.get(
    "/admin/all-users",
    response_model=List[UserResponse],
    tags=["Authentication"],
    summary="List all registered users (Admin only)",
    description=f"""
Returns a list of all users in the system.
Restricted to authenticated users with the `admin` role.
rate-limited {settings.ADMIN_AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def list_all_users(request: Request):
    try:
        return await get_all_users()
    except AppException as ae:
        logger.warning("[ADMIN] %s", ae.message)
        raise ae
    except Exception:
        logger.exception("[ADMIN] Failed to list users")
        raise AppException.from_internal_error("Failed to list users", domain="auth")


@router.post(
    "/admin/find-user",
    response_model=UserResponse,
    tags=["Authentication"],
    summary="Find a user by ID, email, or name (Admin only)",
    description=f"""
Looks up a single user using one of: user_id, email, or full name.
If no match is found, returns a 404-style error.
Must be authenticated as an admin.
rate-limited by {settings.ADMIN_AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def find_user_endpoint(request: Request, payload: UserLookupPayload):
    try:
        user = await find_user_info(payload.user_id, payload.email, payload.name)
        if not user:
            raise AuthValidationError("User not found")
        logger.info("[ADMIN] Found user | identifier=%s", payload)
        return user
    except AppException as ae:
        logger.warning("[ADMIN] %s | payload=%s", ae.message, payload)
        raise ae
    except Exception:
        logger.exception("[ADMIN] Failed to find user | payload=%s", payload)
        raise AppException.from_internal_error("Failed to find user", domain="auth")


@router.delete(
    "/admin/delete-user",
    response_model=dict,
    tags=["Authentication"],
    summary="Delete a user by identifier (Admin only)",
    description=f"""
Deletes a user from the system using ID, email, or full name.
Requires admin privileges and is rate-limited.
rate-limited by {settings.ADMIN_AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def delete_user(request: Request, payload: UserLookupPayload):
    try:
        email = await delete_user_by_identifier(payload.user_id, payload.email, payload.name)
        logger.info("[ADMIN] Deleted user | identifier=%s", email)
        return {"message": f"User {email} deleted successfully"}
    except AppException as ae:
        logger.warning("[ADMIN] %s | payload=%s", ae.message, payload)
        raise ae
    except Exception:
        logger.exception("[ADMIN] Failed to delete user | payload=%s", payload)
        raise AppException.from_internal_error("Failed to delete user", domain="auth")



# ────────────────────────────────────────────────────────
# API KEY MANAGEMENT
# ────────────────────────────────────────────────────────

@router.post(
    "/generate-api-key",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Generate a new API key for the current user",
    description=f"""
Generates a new API key tied to the authenticated user.
Each key is labeled and hashed internally. The raw key is returned only once.

Authentication:
- Requires a valid JWT token (`Authorization: Bearer <token>`)
- Rate limited {settings.AUTH_RATE_LIMIT}

Returns:
- key: raw API key string (displayed once)
- label: user-defined or default label
- note: reminder to store the key securely
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def generate_api_key(request: Request, body: APIKeyRequest):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        key_obj = await generate_api_key_for_user(user.id, label=body.label)

        APIKeyAuthProcessor.add(APIKeyConfig(
            user_id=user.id,
            key=key_obj.hashed_key,
            role=user.role
        ))  # type: ignore

        logger.info("[AUTH] Generated API key | user=%s | label=%s", user.id, body.label or "default")

        return {
            "key": key_obj.raw_key,
            "label": body.label or "default",
            "note": "Store this securely. It won't be shown again."
        }

    except AppException as ae:
        logger.warning("[AUTH] %s | user=%s | label=%s", ae.message, user.id, body.label)
        raise ae

    except Exception:
        logger.exception("[AUTH] Failed to generate API key | user=%s | label=%s", user.id, body.label)
        raise AppException.from_internal_error("Failed to generate API key", domain="auth")


@router.delete(
    "/delete-api-key",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Delete an existing API key by label",
    description=f"""
Deletes an API key associated with the authenticated user.
You must provide the label of the key you wish to delete.

Authentication:
- Requires a valid JWT token
- API key must belong to the current user
- Rate limited {settings.AUTH_RATE_LIMIT}

Returns:
- Confirmation message on successful deletion
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def delete_api_key(request: Request, payload: APIKeyDeleteRequest):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        deleted_key = await delete_api_key_for_user(user.id, payload.label)
        APIKeyAuthProcessor.remove(deleted_key)

        logger.info("[AUTH] Deleted API key | user=%s | label=%s", user.id, payload.label)

        return {"message": f"API key with label '{payload.label}' has been deleted."}

    except AppException as ae:
        logger.warning("[AUTH] %s | user=%s | label=%s", ae.message, user.id, payload.label)
        raise ae

    except Exception:
        logger.exception("[AUTH] Failed to delete API key | user=%s | label=%s", user.id, payload.label)
        raise AppException.from_internal_error("Failed to delete API key", domain="auth")

# ────────────────────────────────────────────────────────
# PROFILE AND SECRETS
# ────────────────────────────────────────────────────────

@router.get(
    "/profile",
    response_model=dict,
    tags=["Authentication"],
    summary="Get profile information of the authenticated user",
    description=f"""
Returns profile details (e.g., email, role, timestamps) for the authenticated user.
Authentication required via JWT token in `Authorization: Bearer <token>`.
rate-limited {settings.AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def get_user_profile(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        profile = await get_user_profile_data(user.id)
        logger.info("[AUTH] Retrieved profile | user=%s", user.id)
        return profile

    except AppException as ae:
        logger.warning("[AUTH] %s | user=%s", ae.message, user.id)
        raise ae

    except Exception:
        logger.exception("[AUTH] Failed to retrieve profile | user=%s", user.id)
        raise AppException.from_internal_error("Failed to retrieve user profile", domain="auth")


@router.post(
    "/secret-info",
    response_model=List[SecretInfo],
    tags=["Authentication"],
    summary="List secrets associated with the current user",
    description=f"""
Returns a list of all secrets belonging to the current user.
Optional filtering by active/inactive status.
Authentication required via JWT token.
rate-limited {settings.AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def get_user_secret_info(request: Request, payload: SecretLabelQuery):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        secrets = await get_secret_info_for_user(user.id, is_active=payload.is_active)
        logger.info("[AUTH] Retrieved secrets | user=%s | active=%s | count=%d", user.id, payload.is_active, len(secrets))
        return secrets

    except AppException as ae:
        logger.warning("[AUTH] %s | user=%s | active=%s", ae.message, user.id, payload.is_active)
        raise ae

    except Exception:
        logger.exception("[AUTH] Failed to retrieve secrets | user=%s | active=%s", user.id, payload.is_active)
        raise AppException.from_internal_error("Failed to retrieve secret info", domain="auth")


@router.post(
    "/create-secret",
    response_model=SecretCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Create a new secret for the current user",
    description=f"""
Creates a new secret used to sign webhook payloads.
User is limited to a maximum number of secrets (configured in the environment).
Authentication required.
rate-limited {settings.AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def create_user_secret_endpoint(request: Request, payload: SecretCreateRequest):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        secret = await create_secret_for_user(user.id, payload)
        logger.info("[AUTH] Created secret | user=%s | label=%s", user.id, payload.label)
        return secret

    except AppException as ae:
        logger.warning("[AUTH] %s | user=%s | payload=%s", ae.message, user.id, payload)
        raise ae

    except Exception:
        logger.exception("[AUTH] Failed to create secret | user=%s | payload=%s", user.id, payload)
        raise AppException.from_internal_error("Secret creation failed", domain="auth")


@router.delete(
    "/delete-secret",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Delete a secret by label",
    description=f"""
Deletes an existing secret for the current user using its label.
Authentication required.
rate-limited {settings.AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def delete_secret(request: Request, payload: SecretLabelPayload):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        label = await delete_secret_by_label(user.id, payload.label)
        logger.info("[AUTH] Deleted secret | user=%s | label=%s", user.id, label)
        return {"message": f"Secret with label '{label}' has been deleted."}

    except AppException as ae:
        logger.warning("[AUTH] %s | user=%s | label=%s", ae.message, user.id, payload.label)
        raise ae

    except Exception:
        logger.exception("[AUTH] Failed to delete secret | user=%s | label=%s", user.id, payload.label)
        raise AppException.from_internal_error("Failed to delete secret", domain="auth")


@router.post(
    "/toggle-secret",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Activate or deactivate a secret by label",
    description=f"""
Changes the active status of a secret.
Useful for temporarily disabling a webhook secret without deleting it.
Authentication required.
rate-limited {settings.AUTH_RATE_LIMIT}.
"""
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def toggle_secret(request: Request, payload: SecretTogglePayload):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        label = await set_secret_active_status(user.id, payload.label, payload.is_active)
        state = "activated" if payload.is_active else "deactivated"
        logger.info("[AUTH] Toggled secret | user=%s | label=%s | new_state=%s", user.id, label, state)
        return {"message": f"Secret with label '{label}' has been {state}."}

    except AppException as ae:
        logger.warning("[AUTH] %s | user=%s | label=%s", ae.message, user.id, payload.label)
        raise ae

    except Exception:
        logger.exception("[AUTH] Failed to toggle secret | user=%s | label=%s", user.id, payload.label)
        raise AppException.from_internal_error("Failed to toggle secret", domain="auth")
