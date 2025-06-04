from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List

from app.domain.auth_logic import onboard_users_from_names

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
