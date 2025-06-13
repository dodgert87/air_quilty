from typing import List, Optional
from uuid import UUID
import re

from app.infrastructure.database.repository import secret_repository
from app.infrastructure.database.repository import user_repository
from app.utils.validators import validate_password_complexity
from app.models.DB_tables.user_secrets import UserSecret
from app.models.DB_tables.user import User
from app.infrastructure.database.repository import api_key_repository
from app.utils.jwt_utils import decode_jwt, decode_jwt_unverified, generate_jwt
from app.models.schemas.rest.auth_schemas import LoginResponse, NewUserInput, OnboardResult
from app.utils.secret_utils import generate_api_key, generate_secret, get_api_key_expiry, get_secret_expiry
from app.utils.hashing import hash_value, verify_value
from app.utils.config import settings
from app.infrastructure.database.repository.user_repository import get_user_by_email, create_user, get_user_by_id, update_last_login
from app.infrastructure.database.repository.secret_repository import create_user_secret, get_all_active_user_secrets
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.exceptions_base import AppException, AuthValidationError, UserNotFoundError, AuthConflictError


async def onboard_users_from_inputs(users: List[NewUserInput]) -> OnboardResult:
    created_users: List[str] = []
    skipped_users: List[str] = []

    async with run_in_transaction() as db:
        for user in users:
            name = user.name.strip()
            first, last = parse_full_name(name)
            email = f"{first.lower()}.{last.lower()}@tuni.fi"

            existing = await get_user_by_email(db, email)
            if existing:
                skipped_users.append(email)
                continue

            hashed_pw = hash_value(settings.DEFAULT_USER_PASSWORD)

            new_user = await create_user(
                db,
                email=email,
                username=f"{first}_{last}".lower(),
                hashed_password=hashed_pw,
                role=user.role
            )

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


async def change_user_password(user: User, old_password: str, new_password: str, label: str | None = None):
    if not verify_value(old_password, user.hashed_password):
        raise AuthValidationError("Old password is incorrect")

    if not validate_password_complexity(new_password):
        raise AuthValidationError("New password does not meet complexity requirements")

    hashed = hash_value(new_password)

    async with run_in_transaction() as session:
        await user_repository.update_user_password(session, user.id, hashed)
        await secret_repository.revoke_all_user_secrets(session, user.id)
        await api_key_repository.revoke_all_user_api_keys(session, user.id)

        await secret_repository.create_user_secret(
            session,
            user_id=user.id,
            secret=hash_value(generate_secret()),
            label=label or "reset",
            is_active=True,
            expires_at=get_secret_expiry()
        )


async def login_user(email: str, password: str) -> LoginResponse:
    async with run_in_transaction() as db:
        user = await get_user_by_email(db, email)
        if not user or not verify_value(password, user.hashed_password):
            raise AuthValidationError("Invalid email or password")

        _, active_secret = await get_user_and_active_secret(user.id)

        await update_last_login(db, user.id)

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
            raise AuthValidationError("Token missing 'sub' claim")

        secrets = await get_all_active_user_secrets(db, user_id)
        if not secrets:
            raise AuthValidationError("No active secrets")

        for s in secrets:
            try:
                decode_jwt(token, s.secret)
                break
            except Exception:
                continue
        else:
            raise AuthValidationError("Invalid or expired token")

        user = await get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundError("User for valid token")

        return user


async def generate_api_key_for_user(user_id: UUID, label: str) -> str:
    async with run_in_transaction() as session:
        keys = await api_key_repository.get_api_keys_by_user(session, user_id)

        if len(keys) >= settings.MAX_API_KEYS_PER_USER:
            raise AuthConflictError("API key limit reached")

        if any(k.label == label for k in keys):
            raise AuthConflictError(f"API key label '{label}' already in use")

        raw_key = generate_api_key()
        hashed_key = hash_value(raw_key)

        for existing in keys:
            if verify_value(raw_key, existing.key):
                raise AuthConflictError("Generated API key matches existing one — try again")

        await api_key_repository.create_api_key(
            session,
            user_id,
            hashed_key,
            label=label,
            expires_at=get_api_key_expiry()
        )

    return raw_key


async def validate_api_key(api_key: str) -> User:
    async with run_in_transaction() as session:
        all_keys = await api_key_repository.get_all_active_keys(session)

        for key_obj in all_keys:
            if verify_value(api_key, key_obj.key):
                user = await get_user_by_id(session, key_obj.user_id)
                if not user:
                    raise UserNotFoundError("User for API key")
                return user

        raise AuthValidationError("Invalid or inactive API key")


async def delete_api_key_for_user(user_id: UUID, label: str) -> None:
    async with run_in_transaction() as session:
        deleted = await api_key_repository.delete_api_key_by_label(session, user_id, label)
        if not deleted:
            raise UserNotFoundError(f"API key with label '{label}'")


def parse_full_name(name: str) -> tuple[str, str]:
    parts = re.split(r"\s+", name.strip())
    if len(parts) < 2:
        return parts[0], "unknown"
    return parts[0], parts[-1]


async def get_user_and_active_secret(user_id: UUID) -> tuple[User, UserSecret]:
    async with run_in_transaction() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            raise UserNotFoundError()

        secrets = await get_all_active_user_secrets(session, user_id)
        if not secrets:
            raise AuthValidationError("No active secret found for user")

        return user, secrets[0]


async def get_user_profile_data(user_id: UUID) -> dict:
    async with run_in_transaction() as session:
        user = await user_repository.get_user_by_id(session, user_id)
        if not user:
            raise UserNotFoundError()

        secrets = await secret_repository.get_user_secrets(session, user.id)
        secret_data = [
            {"label": s.label or "unnamed", "active": s.is_active} for s in secrets
        ]

        api_keys = await api_key_repository.get_api_keys_by_user(session, user.id)
        api_key_data = [
            {"label": k.label or "unnamed", "active": k.is_active} for k in api_keys
        ]

        return {
            "email": user.email,
            "role": user.role,
            "last_login": user.last_login,
            "secrets": secret_data,
            "api_keys": api_key_data
        }


async def find_user(user_id: Optional[UUID], email: Optional[str], name: Optional[str]) -> Optional[User]:
    async with run_in_transaction() as session:
        if user_id:
            return await user_repository.get_user_by_id(session, user_id)
        if email:
            return await user_repository.get_user_by_email(session, email)
        if name:
            first, last = parse_full_name(name)
            generated_email = f"{first.lower()}.{last.lower()}@tuni.fi"
            return await user_repository.get_user_by_email(session, generated_email)
        return None


async def delete_user_by_identifier(user_id: Optional[UUID], email: Optional[str], name: Optional[str]) -> str:
    async with run_in_transaction() as session:
        user = await find_user(user_id, email, name)
        if not user:
            raise UserNotFoundError("User not found with the provided identifier")

        await secret_repository.delete_user_secrets(session, user.id)
        await api_key_repository.delete_all_user_api_keys(session, user.id)
        await user_repository.delete_user(session, user.id)

        return user.email


async def get_all_users() -> List[User]:
    async with run_in_transaction() as session:
        return list(await user_repository.get_all_users(session))


async def find_user_info(user_id: Optional[UUID], email: Optional[str], name: Optional[str]) -> Optional[User]:
    async with run_in_transaction() as session:
        return await find_user(user_id, email, name)
