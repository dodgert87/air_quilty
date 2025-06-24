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

# ──────────────── Admin Endpoints ───────────────── #

@router.post("/admin/onboard-users", response_model=OnboardResult, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def onboard_users(request: Request, payload: UserOnboardRequest):
    try:
        result = await onboard_users_from_inputs(payload.users)
        logger.info("[ADMIN] Onboarded users | count=%d", len(payload.users))
        return result
    except Exception as e:
        logger.exception("[ADMIN] Failed to onboard users | payload=%s", payload)
        raise AppException.from_internal_error("Failed to onboard users", domain="auth")


@router.get("/admin/all-users", response_model=List[UserResponse])
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def list_all_users(request: Request):
    """List all registered users (Admin only)."""
    return await get_all_users()


@router.post("/admin/find-user", response_model=UserResponse)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def find_user_endpoint(request: Request, payload: UserLookupPayload):
    try:
        user = await find_user_info(payload.user_id, payload.email, payload.name)
        if not user:
            raise AuthValidationError("User not found")
        logger.info("[ADMIN] Found user | identifier=%s", payload)
        return user
    except AuthValidationError:
        raise  # Let this bubble up unchanged
    except Exception as e:
        logger.exception("[ADMIN] Failed to find user | payload=%s", payload)
        raise AppException.from_internal_error("Failed to find user", domain="auth")



@router.delete("/admin/delete-user", response_model=dict)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def delete_user(request: Request, payload: UserLookupPayload):
    try:
        email = await delete_user_by_identifier(payload.user_id, payload.email, payload.name)
        logger.info("[ADMIN] Deleted user | identifier=%s", email)
        return {"message": f"User {email} deleted successfully"}
    except Exception as e:
        logger.exception("[ADMIN] Failed to delete user | payload=%s", payload)
        raise AppException.from_internal_error("Failed to delete user", domain="auth")

# ──────────────── Authentication Core ───────────── #

@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(request: Request, payload: LoginRequest):
    try:
        response = await login_user(payload.email, payload.password)
        logger.info("[AUTH] Login successful | email=%s", payload.email)
        return response
    except AuthValidationError:
        raise  # Bubble up custom auth errors
    except Exception as e:
        logger.exception("[AUTH] Login failed | email=%s", payload.email)
        raise AppException.from_internal_error("Login failed", domain="auth")



@router.post("/change-password")
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def change_password(payload: ChangePasswordRequest, request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        await change_user_password(user, payload.old_password, payload.new_password, payload.label)
        APIKeyAuthProcessor.invalidate_user(user.id)
        logger.info("[AUTH] Password changed | user=%s", user.id)
        return {"message": "Password updated successfully"}
    except Exception as e:
        logger.exception("[AUTH] Failed to change password | user=%s", user.id)
        raise AppException.from_internal_error("Failed to change password", domain="auth")



@router.get("/test-auth")
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
    except Exception as e:
        logger.exception("[AUTH] Failed during auth test")
        raise AppException.from_internal_error("Failed to verify authentication", domain="auth")


# ──────────────── API Key Management ────────────── #

@router.post("/generate-api-key", response_model=dict, status_code=status.HTTP_201_CREATED)
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
        ))

        logger.info("[AUTH] Generated API key | user=%s | label=%s", user.id, body.label or "default")

        return {
            "key": key_obj.raw_key,
            "label": body.label or "default",
            "note": "Store this securely. It won't be shown again."
        }
    except Exception as e:
        logger.exception("[AUTH] Failed to generate API key | user=%s | label=%s", user.id, body.label)
        raise AppException.from_internal_error("Failed to generate API key", domain="auth")


@router.delete("/delete-api-key", status_code=status.HTTP_200_OK)
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
    except Exception as e:
        logger.exception("[AUTH] Failed to delete API key | user=%s | label=%s", user.id, payload.label)
        raise AppException.from_internal_error("Failed to delete API key", domain="auth")


# ──────────────── Profile and Secrets ───────────── #

@router.get("/profile", response_model=dict)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def get_user_profile(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        profile = await get_user_profile_data(user.id)
        logger.info("[AUTH] Retrieved profile | user=%s", user.id)
        return profile
    except Exception as e:
        logger.exception("[AUTH] Failed to retrieve profile | user=%s", user.id)
        raise AppException.from_internal_error("Failed to retrieve user profile", domain="auth")



@router.post("/secret-info", response_model=List[SecretInfo])
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def get_user_secret_info(request: Request, payload: SecretLabelQuery):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        secrets = await get_secret_info_for_user(user.id, is_active=payload.is_active)
        logger.info("[AUTH] Retrieved secrets | user=%s | active=%s | count=%d", user.id, payload.is_active, len(secrets))
        return secrets
    except Exception as e:
        logger.exception("[AUTH] Failed to retrieve secrets | user=%s | active=%s", user.id, payload.is_active)
        raise AppException.from_internal_error("Failed to retrieve secret info", domain="auth")



@router.post("/create-secret", response_model=SecretCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def create_user_secret_endpoint(request: Request, payload: SecretCreateRequest):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        return await create_secret_for_user(user.id, payload)
    except Exception as e:
        logger.exception("[AUTH] Failed to create secret for user %s | payload=%s", user.id, payload)
        raise AppException.from_internal_error("Secret creation failed", domain="auth")


@router.delete("/delete-secret", status_code=status.HTTP_200_OK)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def delete_secret(request: Request, payload: SecretLabelPayload):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    try:
        label = await delete_secret_by_label(user.id, payload.label)
        logger.info("[AUTH] Deleted secret | user=%s | label=%s", user.id, label)
        return {"message": f"Secret with label '{label}' has been deleted."}
    except Exception as e:
        logger.exception("[AUTH] Failed to delete secret | user=%s | label=%s", user.id, payload.label)
        raise AppException.from_internal_error("Failed to delete secret", domain="auth")


@router.post("/toggle-secret", status_code=status.HTTP_200_OK)
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
    except Exception as e:
        logger.exception("[AUTH] Failed to toggle secret | user=%s | label=%s", user.id, payload.label)
        raise AppException.from_internal_error("Failed to toggle secret", domain="auth")
