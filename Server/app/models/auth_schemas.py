from typing import List
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class OnboardResult(BaseModel):
    created_count: int
    users: List[str]
    skipped: List[str]