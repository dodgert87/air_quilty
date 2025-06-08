from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class NewUserInput(BaseModel):
    name: str
    role: Literal["admin", "developer", "authenticated", "guest"]

class UserOnboardRequest(BaseModel):
    users: List[NewUserInput]

class OnboardResult(BaseModel):
    created_count: int
    users: List[str]        # newly created emails
    skipped: List[str]      # emails that already existed


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    label: Optional[str] = Field(None, max_length=50, description="Optional label for new login secret")

class APIKeyRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)

class APIKeyDeleteRequest(BaseModel):
    label: str = Field(..., min_length=1, description="Label of the API key to delete")