from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, SecretStr

from app.models.DB_tables.user import RoleEnum

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

class UserDeleteRequest(BaseModel):
    id: Optional[UUID] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, description="Full name (first + last)")

    def one_field_provided(self) -> bool:
        return any([self.id, self.email, self.name])

class UserLookupPayload(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, description="Full name (e.g., John Doe)")


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    role: RoleEnum
    created_at: datetime
    last_login: Optional[datetime]

class SecretLabelQuery(BaseModel):
    is_active: Optional[bool] = None

class SecretCreateRequest(BaseModel):
    label: str
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = True

class SecretCreateResponse(BaseModel):
    label: str
    secret: str  # plain text, returned once

class SecretLabelPayload(BaseModel):
    label: str

class SecretTogglePayload(BaseModel):
    label: str
    is_active: bool


class SecretInfo(BaseModel):
    label: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

class APIKeyConfig(BaseModel):
    key: SecretStr  # primary key
    user_id: UUID
    expires_at: datetime | None = None
    role: RoleEnum

class GeneratedAPIKey(BaseModel):
    raw_key: str
    hashed_key: SecretStr