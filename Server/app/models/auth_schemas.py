from typing import List
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserNameList(BaseModel):
    names: List[str]  # e.g. ["John Doe", "Alice Smith"]

class OnboardResult(BaseModel):
    created_count: int
    users: List[str]        # newly created emails
    skipped: List[str]      # emails that already existed
