from typing import List
from uuid import UUID
import re

from app.models.user_secrets import UserSecret
from app.models.user import User
from app.infrastructure.database import api_key_repository
from app.utils.jwt_utils import decode_jwt, decode_jwt_unverified, generate_jwt
from app.models.auth_schemas import LoginResponse, OnboardResult
from app.utils.secret_utils import generate_api_key, generate_secret, get_secret_expiry
from app.utils.hashing import hash_value, verify_value
from app.utils.config import settings
from app.infrastructure.database.user_repository import get_user_by_email, create_user, get_user_by_id
from app.infrastructure.database.secret_repository import create_user_secret, get_all_active_user_secrets
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
            hashed_pw = hash_value(settings.DEFAULT_USER_PASSWORD)
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
                secret=hash_value(generate_secret()),
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
        if not user or not verify_value(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        # Fetch one active secret for signing
        _, active_secret = await get_user_and_active_secret(user.id)

        token, expires_in = generate_jwt(
            user_id=str(user.id),
            role=user.role,
            secret=active_secret.secret
        )

        return LoginResponse(
            access_token=token,
            expires_in=expires_in
        )

async def validate_token_and_get_user(token: str) -> User:
    async with run_in_transaction() as db:
        unverified = decode_jwt_unverified(token)
        user_id = unverified.get("sub")
        if not user_id:
            raise ValueError("Token missing 'sub' claim")

        secrets = await get_all_active_user_secrets(db, user_id)
        if not secrets:
            raise ValueError("No active secrets")

        for s in secrets:
            try:
                decode_jwt(token, s.secret)
                break
            except Exception:
                continue
        else:
            raise ValueError("Invalid or expired token")

        user = await get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")

        return user


async def generate_api_key_for_user(user_id: UUID, label: str | None = None) -> str:
    async with run_in_transaction() as session:
        keys = await api_key_repository.get_api_keys_by_user(session, user_id)
        if len(keys) >= settings.MAX_API_KEYS_PER_USER:
            raise ValueError("API key limit reached")

        raw_key = generate_api_key()
        hashed_key = hash_value(raw_key)

        #check for accidental hash collision (rare)
        for existing in keys:
            if verify_value(raw_key, existing.key):
                raise ValueError("Generated API key matches existing one — try again")

        await api_key_repository.create_api_key(
            session, user_id, hashed_key, label=label
        )

    return raw_key

async def validate_api_key(api_key: str) -> User:
    async with run_in_transaction() as session:
        # Step 1: Get all active keys
        all_keys = await api_key_repository.get_all_active_keys(session)

        # Step 2: Compare in Python using bcrypt-safe compare
        for key_obj in all_keys:
            if verify_value(api_key, key_obj.key):  # key_obj.key is hashed
                user = await get_user_by_id(session, key_obj.user_id)
                if not user:
                    raise ValueError("User not found for this API key")
                return user

        raise ValueError("Invalid or inactive API key")

def parse_full_name(name: str) -> tuple[str, str]:
    parts = re.split(r"\s+", name.strip())
    if len(parts) < 2:
        return parts[0], "unknown"
    return parts[0], parts[-1]



async def get_user_and_active_secret(user_id: UUID) -> tuple[User, UserSecret]:
    async with run_in_transaction() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            raise ValueError("User not found")

        secrets = await get_all_active_user_secrets(session, user_id)
        if not secrets:
            raise ValueError("No active secret found for user")

        return user, secrets[0]