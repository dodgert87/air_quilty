from fastapi import APIRouter, Request, status, Depends
from typing import List

from app.models.auth_schemas import (
    APIKeyDeleteRequest, APIKeyRequest, ChangePasswordRequest, LoginRequest,
    LoginResponse, OnboardResult, UserLookupPayload, UserOnboardRequest, UserResponse
)
from app.domain.auth_logic import (
    change_user_password, delete_api_key_for_user, delete_user_by_identifier,
    find_user_info, generate_api_key_for_user, get_all_users,
    get_user_profile_data, login_user, onboard_users_from_inputs
)
from app.utils.exceptions_base import AuthValidationError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/admin/onboard-users", response_model=OnboardResult, status_code=status.HTTP_201_CREATED)
async def onboard_users(payload: UserOnboardRequest):
    return await onboard_users_from_inputs(payload.users)


@router.get("/admin/all-users", response_model=List[UserResponse])
async def list_all_users():
    return await get_all_users()


@router.post("/admin/find-user", response_model=UserResponse)
async def find_user_endpoint(payload: UserLookupPayload):
    user = await find_user_info(payload.user_id, payload.email, payload.name)
    if not user:
        raise AuthValidationError("User not found")
    return user


@router.delete("/admin/delete-user", response_model=dict)
async def delete_user(payload: UserLookupPayload):
    email = await delete_user_by_identifier(payload.user_id, payload.email, payload.name)
    return {"message": f"User {email} deleted successfully"}


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    return await login_user(payload.email, payload.password)


@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    await change_user_password(user, payload.old_password, payload.new_password, payload.label)
    return {"message": "Password updated successfully"}


@router.get("/test-auth")
async def test_auth(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        return {"message": "No user authenticated (guest access)"}

    return {
        "message": "Authenticated user",
        "user_id": str(user.id),
        "role": user.role,
        "email": user.email
    }


@router.post("/generate-api-key", response_model=dict, status_code=status.HTTP_201_CREATED)
async def generate_api_key(request: Request, body: APIKeyRequest):
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
async def delete_api_key(request: Request, payload: APIKeyDeleteRequest):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    await delete_api_key_for_user(user.id, payload.label)
    return {"message": f"API key with label '{payload.label}' has been deleted."}


@router.get("/profile", response_model=dict)
async def get_user_profile(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthValidationError("Authentication required")

    return await get_user_profile_data(user.id)
