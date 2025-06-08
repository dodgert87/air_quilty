from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from typing import List

from app.models.auth_schemas import APIKeyDeleteRequest, APIKeyRequest, ChangePasswordRequest, LoginRequest, LoginResponse, OnboardResult, UserOnboardRequest
from app.domain.auth_logic import change_user_password, delete_api_key_for_user, generate_api_key_for_user, get_user_profile_data, login_user, onboard_users_from_inputs

router = APIRouter(prefix="/auth", tags=["Authentication"])



@router.post("/admin/onboard-users", response_model=OnboardResult, status_code=status.HTTP_201_CREATED)
async def onboard_users(payload: UserOnboardRequest):
    """
    Admin-only endpoint to create users in bulk from name + role input.
    """
    try:
        result = await onboard_users_from_inputs(payload.users)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to onboard users: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    try:
        return await login_user(payload.email, payload.password)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, request: Request):
    user = request.state.user
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        await change_user_password(user, payload.old_password, payload.new_password, payload.label) # type: ignore
        return {"message": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    """
    Generates a new API key for the authenticated user with optional label.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        key = await generate_api_key_for_user(user.id, label=body.label)
        return {
            "key": key,  # only shown once
            "label": body.label or "default",
            "note": "Store this securely. It won't be shown again."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error during API key generation.")

@router.delete("/delete-api-key", status_code=status.HTTP_200_OK)
async def delete_api_key(request: Request, payload: APIKeyDeleteRequest):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        await delete_api_key_for_user(user.id, payload.label)
        return {"message": f"API key with label '{payload.label}' has been deleted."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error during API key deletion")


@router.get("/profile", response_model=dict)
async def get_user_profile(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        return await get_user_profile_data(user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")