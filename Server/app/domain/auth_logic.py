from typing import List
import jwt
from pydantic import BaseModel
import re

from app.utils.jwt_utils import decode_jwt, generate_jwt
from app.models.auth_schemas import LoginResponse, OnboardResult
from app.utils.secret_utils import generate_secret, get_secret_expiry
from app.utils.hashing import hash_password, verify_password
from app.utils.config import settings
from app.infrastructure.database.user_repository import get_user_by_email, create_user, get_user_by_id
from app.infrastructure.database.secret_repository import create_user_secret, get_active_user_secret
from app.infrastructure.database.transaction import run_in_transaction





async def onboard_users_from_names(names: List[str]) -> OnboardResult:
    from sqlalchemy.ext.asyncio import AsyncSession

    created_users: List[str] = []
    skipped_users: List[str] = []

    async with run_in_transaction() as db:
        for name in names:
            name = name.strip()
            first, last = parse_full_name(name)
            email = f"{first.lower()}.{last.lower()}@tuni.fi"

            existing = await get_user_by_email(db, email)
            if existing:
                skipped_users.append(email)
                continue

            # Create user
            hashed_pw = hash_password(settings.DEFAULT_USER_PASSWORD)
            new_user = await create_user(
                db,
                email=email,
                username=f"{first}_{last}".lower(),
                hashed_password=hashed_pw,
                role="authenticated"
            )

            # Create secret (we rely on is_active = True to determine "current")
            await create_user_secret(
                db,
                user_id=new_user.id,
                secret=generate_secret(),
                label="temp",
                is_active=True,
                expires_at=get_secret_expiry()
            )

            created_users.append(email)

    return OnboardResult(
        created_count=len(created_users),
        users=created_users,
        skipped=skipped_users
    )

async def login_user(email: str, password: str) -> LoginResponse:
    from app.infrastructure.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user = await get_user_by_email(db, email)
        if not user:
            raise ValueError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        secret = await get_active_user_secret(db, user.id)
        if not secret:
            raise ValueError("No active secret found for user")

        token, expires_in = generate_jwt(
            user_id=str(user.id),
            role=user.role,
            secret=secret.secret
        )

        return LoginResponse(
            access_token=token,
            expires_in=expires_in
        )

async def validate_token_and_get_user(token: str):
    from sqlalchemy.ext.asyncio import AsyncSession

    async with run_in_transaction() as db:

        # Step 1: decode token without secret to extract user_id
        unverified = jwt.decode(token, options={"verify_signature": False})
        user_id = unverified.get("sub")
        if not user_id:
            raise ValueError("Token missing user ID (sub)")

        # Step 2: load user + secret
        secret = await get_active_user_secret(db, user_id)
        if not secret:
            raise ValueError("No active secret found for token")

        # Step 3: fully verify token
        payload = decode_jwt(token, secret.secret)

        # Optional: fetch user object if needed
        user = await get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")

        return {
            "user_id": user_id,
            "role": payload.get("role"),
            "user": user
        }

def parse_full_name(name: str) -> tuple[str, str]:
    parts = re.split(r"\s+", name.strip())
    if len(parts) < 2:
        return parts[0], "unknown"
    return parts[0], parts[-1]
