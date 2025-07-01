from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, SecretStr

from app.models.DB_tables.user import RoleEnum


# -------------------------------
# AUTHENTICATION
# -------------------------------

class LoginRequest(BaseModel):
    """Login credentials for generating a JWT token."""
    email: EmailStr = Field(..., description="User email address", example="user@example.com") # type: ignore
    password: str = Field(..., min_length=8, description="Plaintext password", example="mySecurePass123") # type: ignore


class LoginResponse(BaseModel):
    """Successful login response containing the JWT access token."""
    access_token: str = Field(..., description="JWT token string")
    token_type: str = Field(default="bearer", description="Authentication scheme (always 'bearer')")
    expires_in: int = Field(..., description="Token validity in seconds", example=3600) # type: ignore


class ChangePasswordRequest(BaseModel):
    """Request to change the user's password.

    Replaces the login secret and invalidates all sessions and API keys.
    """
    old_password: str = Field(..., min_length=8, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


# -------------------------------
# USER ONBOARDING & MANAGEMENT
# -------------------------------

class NewUserInput(BaseModel):
    """User details used during bulk onboarding."""
    name: str = Field(..., description="Full name (first and last)", example="Alice Smith") # type: ignore
    role: Literal["admin", "developer", "authenticated", "guest"] = Field(..., description="Assigned user role")


class UserOnboardRequest(BaseModel):
    """Request to create multiple users silently.

    Users are created using a default password defined in environment variables.
    No notification or email is sent.
    """
    users: List[NewUserInput]


class OnboardResult(BaseModel):
    """Result of the user onboarding operation."""
    created_count: int = Field(..., description="Number of users successfully created")
    users: List[str] = Field(..., description="Emails of the newly created users")
    skipped: List[str] = Field(..., description="Emails that were skipped (already existed)")


class UserDeleteRequest(BaseModel):
    """Delete a user by ID, email, or name (any one field is required)."""
    id: Optional[UUID] = Field(None, description="User UUID")
    email: Optional[EmailStr] = Field(None, description="User email address")
    name: Optional[str] = Field(None, description="Full name (first and last)")

    def one_field_provided(self) -> bool:
        return any([self.id, self.email, self.name])


class UserLookupPayload(BaseModel):
    """Payload to look up a user by ID, email, or name."""
    user_id: Optional[UUID] = Field(None, description="User UUID")
    email: Optional[EmailStr] = Field(None, description="User email address")
    name: Optional[str] = Field(None, description="Full name (e.g., John Doe)")


class UserResponse(BaseModel):
    """Response with detailed user information."""
    id: UUID = Field(..., description="Unique user ID")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Display name or full name")
    role: RoleEnum = Field(..., description="Role assigned to the user")
    created_at: datetime = Field(..., description="Timestamp when the user was created")
    last_login: Optional[datetime] = Field(None, description="Timestamp of last login (if available)")


# -------------------------------
# API KEY MANAGEMENT
# -------------------------------

class APIKeyRequest(BaseModel):
    """Request to generate a new API key with a label."""
    label: str = Field(..., min_length=1, max_length=100, description="Custom label for the new API key")


class APIKeyDeleteRequest(BaseModel):
    """Delete an API key using its public label.

    Labels are unique per user. Internal IDs are never exposed.
    """
    label: str = Field(..., min_length=1, description="Label of the API key to delete")


class APIKeyConfig(BaseModel):
    """Internal structure for storing a hashed API key."""
    key: SecretStr
    user_id: UUID
    expires_at: Optional[datetime] = Field(None, description="Optional expiry timestamp")
    role: RoleEnum = Field(..., description="Associated role")


class GeneratedAPIKey(BaseModel):
    """Response model for newly generated API keys."""
    raw_key: str = Field(..., description="The actual key string (visible only once)")
    hashed_key: SecretStr = Field(..., description="Securely stored hashed version of the key")


# -------------------------------
# SECRET MANAGEMENT
# -------------------------------

class SecretLabelQuery(BaseModel):
    """Filter secrets by their active status."""
    is_active: Optional[bool] = Field(None, description="Whether to fetch only active/inactive secrets")


class SecretCreateRequest(BaseModel):
    """Request to create a new secret key for webhook signing.

    Users may have a limited number of secrets (e.g., 3), configured via environment.
    """
    label: str = Field(..., description="Unique label for the secret")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration timestamp")
    is_active: Optional[bool] = Field(default=True, description="Whether the secret is active immediately")


class SecretCreateResponse(BaseModel):
    """Response with the created secret (returned only once)."""
    label: str = Field(..., description="Secret label")
    secret: str = Field(..., description="Raw secret string (displayed only at creation time)")


class SecretLabelPayload(BaseModel):
    """Payload to reference a secret by its label."""
    label: str = Field(..., description="Label of the target secret")


class SecretTogglePayload(BaseModel):
    """Request to enable or disable an existing secret."""
    label: str = Field(..., description="Label of the secret")
    is_active: bool = Field(..., description="Set to True to activate, False to deactivate")


class SecretInfo(BaseModel):
    """Detailed info about a secret."""
    label: str = Field(..., description="Secret label")
    is_active: bool = Field(..., description="Whether the secret is currently active")
    created_at: datetime = Field(..., description="Timestamp when the secret was created")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp (if set)")
