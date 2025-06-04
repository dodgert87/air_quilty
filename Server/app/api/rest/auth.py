from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from typing import List

from app.models.auth_schemas import LoginRequest, LoginResponse
from app.domain.auth_logic import login_user, onboard_users_from_names

router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserNameList(BaseModel):
    names: List[str]  # e.g. ["John Doe", "Alice Smith"]

class OnboardResult(BaseModel):
    created_count: int
    users: List[str]        # newly created emails
    skipped: List[str]      # emails that already existed



@router.post("/onboard-users", response_model=OnboardResult, status_code=status.HTTP_201_CREATED)
async def onboard_users(payload: UserNameList):
    """
    Admin-only endpoint to create users in bulk from a list of names.
    Returns a breakdown of created and skipped users.
    """
    try:
        result = await onboard_users_from_names(payload.names)
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


@router.get("/test-auth")
async def test_auth(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        return {"message": "No user authenticated (guest access)"}
    return {
        "message": "Authenticated user",
        "user_id": user["user_id"],
        "role": user["role"],
        "email": user["user"].email  # You fetched user in `validate_token_and_get_user`
    }