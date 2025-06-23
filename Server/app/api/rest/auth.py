from fastapi import APIRouter, Request, status
from typing import List
from app.utils.config import settings
from app.middleware.rate_limit_middleware import limiter
from app.models.schemas.rest.auth_schemas import (
    APIKeyDeleteRequest, APIKeyRequest, ChangePasswordRequest, LoginRequest,
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
from app.utils.exceptions_base import AuthValidationError

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ──────────────── Admin Endpoints ───────────────── #

@router.post("/admin/onboard-users", response_model=OnboardResult, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def onboard_users(request: Request, payload: UserOnboardRequest):
    """Onboard new users in bulk (Admin only)."""
    return await onboard_users_from_inputs(payload.users)


@router.get("/admin/all-users", response_model=List[UserResponse])
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def list_all_users(request: Request):
    """List all registered users (Admin only)."""
    return await get_all_users()


@router.post("/admin/find-user", response_model=UserResponse)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def find_user_endpoint(request: Request, payload: UserLookupPayload):
    """Find a user by ID, name, or email (Admin only)."""
    user = await find_user_info(payload.user_id, payload.email, payload.name)
    if not user:
        raise AuthValidationError("User not found")
    return user


@router.delete("/admin/delete-user", response_model=dict)
@limiter.limit(settings.ADMIN_AUTH_RATE_LIMIT)
async def delete_user(request: Request, payload: UserLookupPayload):
    """Delete a user (Admin only)."""
    email = await delete_user_by_identifier(payload.user_id, payload.email, payload.name)
    return {"message": f"User {email} deleted successfully"}

# ──────────────── Authentication Core ───────────── #

@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(request: Request, payload: LoginRequest):
    """Login using email and password. Returns access token."""
    return await login_user(payload.email, payload.password)


@router.post("/change-password")
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def change_password(payload: ChangePasswordRequest, request: Request):
    """Authenticated user can change their password using current credentials."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")
    await change_user_password(user, payload.old_password, payload.new_password, payload.label)
    return {"message": "Password updated successfully"}


@router.get("/test-auth")
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def test_auth(request: Request):
    """Verify whether the current request is authenticated and return basic user info."""
    user = getattr(request.state, "user", None)
    if user is None:
        return {"message": "No user authenticated (guest access)"}
    return {
        "message": "Authenticated user",
        "user_id": str(user.id),
        "role": user.role,
        "email": user.email
    }

# ──────────────── API Key Management ────────────── #

@router.post("/generate-api-key", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def generate_api_key(request: Request, body: APIKeyRequest):
    """Generate a new API key for the authenticated user."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")
    key = await generate_api_key_for_user(user.id, label=body.label)
    return {
        "key": key,
        "label": body.label or "default",
        "note": "Store this securely. It won't be shown again."
    }


@router.delete("/delete-api-key", status_code=status.HTTP_200_OK)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def delete_api_key(request: Request, payload: APIKeyDeleteRequest):
    """Delete a user's API key by label."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")
    await delete_api_key_for_user(user.id, payload.label)
    return {"message": f"API key with label '{payload.label}' has been deleted."}

# ──────────────── Profile and Secrets ───────────── #

@router.get("/profile", response_model=dict)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def get_user_profile(request: Request):
    """Get profile information for the authenticated user."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")
    return await get_user_profile_data(user.id)


@router.post("/secret-info", response_model=List[SecretInfo])
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def get_user_secret_info(request: Request, payload: SecretLabelQuery):
    """Get a list of the user's secrets (filtered by active/inactive)."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")
    return await get_secret_info_for_user(user.id, is_active=payload.is_active)


@router.post("/create-secret", response_model=SecretCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def create_user_secret_endpoint(request: Request, payload: SecretCreateRequest):
    """Create a new secret for the user."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")
    return await create_secret_for_user(user.id, payload)


@router.delete("/delete-secret", status_code=status.HTTP_200_OK)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def delete_secret(request: Request, payload: SecretLabelPayload):
    """Delete a user's secret by label."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")
    label = await delete_secret_by_label(user.id, payload.label)
    return {"message": f"Secret with label '{label}' has been deleted."}


@router.post("/toggle-secret", status_code=status.HTTP_200_OK)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def toggle_secret(request: Request, payload: SecretTogglePayload):
    """Activate or deactivate a secret."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")
    label = await set_secret_active_status(user.id, payload.label, payload.is_active)
    state = "activated" if payload.is_active else "deactivated"
    return {"message": f"Secret with label '{label}' has been {state}."}
