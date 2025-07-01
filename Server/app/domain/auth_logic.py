from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from loguru import logger
import re

from pydantic import SecretStr

# --- Import internal modules ---
from app.utils.crypto_utils import decrypt_secret, encrypt_secret
from app.utils.hashing import hash_value, verify_value
from app.utils.jwt_utils import decode_jwt, decode_jwt_unverified, generate_jwt
from app.utils.secret_utils import generate_api_key, generate_secret, get_api_key_expiry, get_secret_expiry
from app.utils.config import settings
from app.utils.validators import validate_password_complexity
from app.utils.exceptions_base import (
    AppException, AuthValidationError, UserNotFoundError, AuthConflictError
)

from app.models.DB_tables.user import User
from app.models.DB_tables.user_secrets import UserSecret
from app.models.schemas.rest.auth_schemas import (
    GeneratedAPIKey, LoginResponse, NewUserInput, OnboardResult,
    SecretCreateRequest, SecretCreateResponse, SecretInfo
)

from app.infrastructure.database.transaction import run_in_transaction
from app.infrastructure.database.repository.restAPI import (
    user_repository, secret_repository, api_key_repository
)
from app.infrastructure.database.repository.restAPI.user_repository import (
    get_user_by_email, create_user, get_user_by_id, update_last_login
)
from app.infrastructure.database.repository.restAPI.secret_repository import (
    create_user_secret, delete_user_secret_by_label, get_all_active_user_secrets,
    get_user_secret_by_label, get_user_secret_labels, get_user_secrets_info,
    set_user_secret_active_status
)


# -------------------------------
# USER ONBOARDING
# -------------------------------

# Onboards a list of new users, skipping existing ones
async def onboard_users_from_inputs(users: List[NewUserInput]) -> OnboardResult:
    created_users: List[str] = []
    skipped_users: List[str] = []

    async with run_in_transaction() as db:
        for user in users:
            # Normalize and parse the full name into first and last
            name = user.name.strip()
            first, last = parse_full_name(name)
            email = f"{first.lower()}.{last.lower()}@tuni.fi"

            # Skip user if email already exists
            existing = await get_user_by_email(db, email)
            if existing:
                logger.info("[AUTH] Skipping existing user | email=%s", email)
                skipped_users.append(email)
                continue

            # Generate hashed default password
            hashed_pw = hash_value(settings.DEFAULT_USER_PASSWORD.get_secret_value())

            try:
                # Create user entry
                new_user = await create_user(
                    db,
                    email=email,
                    username=f"{first}_{last}".lower(),
                    hashed_password=hashed_pw,
                    role=user.role
                )

                # Create default login secret
                await create_user_secret(
                    db,
                    user_id=new_user.id,
                    secret=encrypt_secret(generate_secret()),
                    label="login",
                    is_active=True,
                    expires_at=get_secret_expiry()
                )

                created_users.append(email)
                logger.info("[AUTH] User onboarded | email=%s | role=%s", email, user.role)

            except Exception as e:
                logger.exception("[AUTH] Failed to onboard user | name=%s | email=%s", name, email)
                skipped_users.append(email)  # Could separate failed vs skipped

    logger.info("[AUTH] Onboarding completed | created=%d | skipped=%d", len(created_users), len(skipped_users))

    return OnboardResult(
        created_count=len(created_users),
        users=created_users,
        skipped=skipped_users
    )



# -------------------------------
# AUTHENTICATION & LOGIN
# -------------------------------

# Changes the user's password after validating the old one
async def change_user_password(user: User, old_password: str, new_password: str):
    # Check if the old password is correct
    if not verify_value(old_password, user.hashed_password):
        logger.warning("[AUTH] Incorrect old password | user_id=%s", user.id)
        raise AuthValidationError("Old password is incorrect")

    # Validate new password complexity (length, symbols, etc.)
    if not validate_password_complexity(new_password):
        logger.warning("[AUTH] Password complexity check failed | user_id=%s", user.id)
        raise AuthValidationError("New password does not meet complexity requirements")

    # Hash the new password
    hashed = hash_value(new_password)

    async with run_in_transaction() as session:
        # Update the user's password in the database
        await user_repository.update_user_password(session, user.id, hashed)

        # Revoke all previous secrets and API keys
        await secret_repository.revoke_all_user_secrets(session, user.id)
        await api_key_repository.revoke_all_user_api_keys(session, user.id)

        # Create a new login secret
        await secret_repository.create_user_secret(
            session,
            user_id=user.id,
            secret=encrypt_secret(generate_secret()),
            label="login",
            is_active=True,
            expires_at=get_secret_expiry()
        )

        logger.info("[AUTH] Password changed successfully | user_id=%s", user.id)


# Logs in a user and returns a JWT token signed using their login secret
async def login_user(email: str, password: str) -> LoginResponse:
    async with run_in_transaction() as db:
        # Look up user by email and check password
        user = await get_user_by_email(db, email)
        if not user or not verify_value(password, user.hashed_password):
            logger.warning("[AUTH] Login failed | email=%s", email)
            raise AuthValidationError("Invalid email or password")

        # Get user's login secret
        login_secret = await get_user_secret_by_label(db, user.id, label="login")
        if not login_secret or not login_secret.is_active:
            logger.warning("[AUTH] Login secret invalid or inactive | user_id=%s", user.id)
            raise AuthValidationError("Login secret not found or inactive")

        # Update last login timestamp
        await update_last_login(db, user.id)

        # Generate JWT signed with login secret
        token, expires_in = generate_jwt(
            user_id=str(user.id),
            role=user.role,
            secret=decrypt_secret(login_secret.secret)
        )

        logger.info("[AUTH] Login successful | user_id=%s | role=%s", user.id, user.role)

        return LoginResponse(access_token=token, expires_in=expires_in)


# Validates JWT and returns the associated user
async def validate_token_and_get_user(token: str) -> User:
    async with run_in_transaction() as db:
        try:
            # Decode token without verifying to extract user ID
            unverified = decode_jwt_unverified(token)
            user_id = unverified.get("sub")
        except Exception as e:
            logger.warning("[AUTH] JWT decode failed (unverified)")
            raise AuthValidationError("Invalid or malformed token")

        if not user_id:
            logger.warning("[AUTH] Token missing sub claim")
            raise AuthValidationError("Token missing 'sub' claim")

        # Retrieve login secret from DB
        login_secret = await get_user_secret_by_label(db, UUID(user_id), label="login")
        if not login_secret or not login_secret.is_active:
            logger.warning("[AUTH] Login secret inactive or missing | user_id=%s", user_id)
            raise AuthValidationError("Login secret not found or inactive")

        try:
            # Fully decode and verify the token using the secret
            decode_jwt(token, secret=decrypt_secret(login_secret.secret))
        except Exception as e:
            logger.warning("[AUTH] Token validation failed | user_id=%s", user_id)
            raise AuthValidationError("Invalid or expired token")

        # Ensure the user still exists in the database
        user = await get_user_by_id(db, UUID(user_id))
        if not user:
            logger.warning("[AUTH] Token matched but user not found | user_id=%s", user_id)
            raise UserNotFoundError("User for valid token")

        logger.info("[AUTH] Token validated | user_id=%s | role=%s", user.id, user.role)
        return user



# -------------------------------
# API KEY MANAGEMENT
# -------------------------------

# Generates a new API key for a user
async def generate_api_key_for_user(user_id: UUID, label: str) -> GeneratedAPIKey:
    async with run_in_transaction() as session:
        # Fetch all existing API keys for this user
        keys = await api_key_repository.get_api_keys_by_user(session, user_id)

        # Enforce max API key count per user
        if len(keys) >= settings.MAX_API_KEYS_PER_USER:
            logger.warning("[API_KEY] Limit reached | user_id=%s", user_id)
            raise AuthConflictError("API key limit reached")

        # Check for label conflicts
        if any(k.label == label for k in keys):
            logger.warning("[API_KEY] Duplicate label | user_id=%s | label=%s", user_id, label)
            raise AuthConflictError(f"API key label '{label}' already in use")

        # Generate a new raw key and hash it
        raw_key = generate_api_key()
        hashed_key = hash_value(raw_key)

        # Ensure new key doesn’t match an existing hash (rare, but safe check)
        for existing in keys:
            if verify_value(raw_key, existing.key):
                logger.warning("[API_KEY] Generated key matched existing key | user_id=%s", user_id)
                raise AuthConflictError("Generated API key matches existing one — try again")

        # Store the new hashed key in DB
        await api_key_repository.create_api_key(
            session, user_id, hashed_key, label, expires_at=get_api_key_expiry()
        )

        logger.info("[API_KEY] Created | user_id=%s | label=%s", user_id, label)

    # Return both raw and hashed key for display + confirmation
    return GeneratedAPIKey(raw_key=raw_key, hashed_key=SecretStr(hashed_key))


# Validates an API key and returns the associated user
async def validate_api_key(api_key: str) -> User:
    async with run_in_transaction() as session:
        # Load all active API keys
        all_keys = await api_key_repository.get_all_active_keys(session)

        # Match input key against stored hashes
        for key_obj in all_keys:
            if verify_value(api_key, key_obj.key):
                user = await get_user_by_id(session, key_obj.user_id)
                if not user:
                    logger.error("[API_KEY] Matched key but user not found | user_id=%s", key_obj.user_id)
                    raise UserNotFoundError("User for API key")

                logger.info("[API_KEY] Validated | user_id=%s", user.id)
                return user

        # No match found
        logger.warning("[API_KEY] Invalid key provided")
        raise AuthValidationError("Invalid or inactive API key")


# Deletes a specific API key for a user by label
async def delete_api_key_for_user(user_id: UUID, label: str) -> str:
    async with run_in_transaction() as session:
        # Attempt to delete key by label
        deleted_key = await api_key_repository.delete_api_key_by_label(session, user_id, label)
        if not deleted_key:
            logger.warning("[API_KEY] Deletion failed | user_id=%s | label=%s", user_id, label)
            raise UserNotFoundError(f"API key with label '{label}' not found")

        logger.info("[API_KEY] Deleted | user_id=%s | label=%s", user_id, label)
        return deleted_key

# -------------------------------
# USER UTILITIES
# -------------------------------

# Splits a full name string into (first_name, last_name)
# If only one word is provided, uses "unknown" as the last name
def parse_full_name(name: str) -> tuple[str, str]:
    parts = re.split(r"\s+", name.strip())
    if len(parts) < 2:
        return parts[0], "unknown"
    return parts[0], parts[-1]


# Retrieves a user and their first active secret
async def get_user_and_active_secret(user_id: UUID) -> tuple[User, UserSecret]:
    async with run_in_transaction() as session:
        # Fetch user object
        user = await get_user_by_id(session, user_id)
        if not user:
            logger.warning("[AUTH] User not found | user_id=%s", user_id)
            raise UserNotFoundError()

        # Get all active secrets for the user
        secrets = await get_all_active_user_secrets(session, user_id)
        if not secrets:
            logger.warning("[AUTH] No active secret found | user_id=%s", user_id)
            raise AuthValidationError("No active secret found for user")

        logger.info("[AUTH] Found user and active secret | user_id=%s", user_id)
        return user, secrets[0]  # Return the first active secret



# -------------------------------
# ADMIN / MAINTENANCE UTILITIES
# -------------------------------

# Retrieves a user's profile including email, role, last login,
# and all associated secrets and API keys
async def get_user_profile_data(user_id: UUID) -> dict:
    async with run_in_transaction() as session:
        user = await user_repository.get_user_by_id(session, user_id)
        if not user:
            logger.warning("[ADMIN] User not found | user_id=%s", user_id)
            raise UserNotFoundError()

        secrets = await secret_repository.get_user_secrets(session, user.id)
        api_keys = await api_key_repository.get_api_keys_by_user(session, user.id)

        logger.info("[ADMIN] Profile fetched | user_id=%s | secrets=%d | api_keys=%d", user_id, len(secrets), len(api_keys))

        return {
            "email": user.email,
            "role": user.role,
            "last_login": user.last_login,
            "secrets": [{"label": s.label or "unnamed", "active": s.is_active} for s in secrets],
            "api_keys": [{"label": k.label or "unnamed", "active": k.is_active} for k in api_keys]
        }


# Searches for a user using one of: user_id, email, or full name.
# If name is provided, attempts to generate an email from it.
async def find_user_info(user_id: Optional[UUID], email: Optional[str], name: Optional[str]) -> Optional[User]:
    async with run_in_transaction() as session:
        if user_id:
            logger.info("[ADMIN] Finding user by ID | user_id=%s", user_id)
            return await user_repository.get_user_by_id(session, user_id)
        if email:
            logger.info("[ADMIN] Finding user by email | email=%s", email)
            return await user_repository.get_user_by_email(session, email)
        if name:
            first, last = parse_full_name(name)
            generated_email = f"{first.lower()}.{last.lower()}@tuni.fi"
            logger.info("[ADMIN] Finding user by name | name=%s | resolved_email=%s", name, generated_email)
            return await user_repository.get_user_by_email(session, generated_email)
        logger.warning("[ADMIN] find_user_info called with no parameters")
        return None


# Deletes a user by identifier (user_id, email, or name).
# Also deletes all secrets and API keys for that user.
async def delete_user_by_identifier(user_id: Optional[UUID], email: Optional[str], name: Optional[str]) -> str:
    async with run_in_transaction() as session:
        user = await find_user_info(user_id, email, name)
        if not user:
            logger.warning("[ADMIN] Delete failed — user not found | id=%s | email=%s | name=%s", user_id, email, name)
            raise UserNotFoundError("User not found with the provided identifier")

        await secret_repository.delete_user_secrets(session, user.id)
        await api_key_repository.delete_all_user_api_keys(session, user.id)
        await user_repository.delete_user(session, user.id)

        logger.info("[ADMIN] Deleted user and associated data | user_id=%s | email=%s", user.id, user.email)
        return user.email


# Retrieves a list of all users in the system
async def get_all_users() -> List[User]:
    async with run_in_transaction() as session:
        users = await user_repository.get_all_users(session)
        logger.info("[ADMIN] Fetched all users | count=%d", len(users))
        return list(users)



# -------------------------------
# SECRET MANAGEMENT
# -------------------------------

# Retrieves metadata (like label, active status, expiry) for a user's secrets.
# Optionally filters by `is_active` status.
async def get_secret_info_for_user(user_id: UUID, is_active: Optional[bool] = None) -> list[SecretInfo]:
    async with run_in_transaction() as session:
        secrets = await get_user_secrets_info(session, user_id, is_active=is_active)
        logger.info("[SECRET] Fetched secret metadata | user_id=%s | is_active=%s | count=%d", user_id, is_active, len(secrets))
        return [SecretInfo(**s) for s in secrets]


# Generates a new random secret, encrypts it, and stores it in the DB.
# The secret is returned only once to the user.
async def create_secret_for_user(user_id: UUID, payload: SecretCreateRequest) -> SecretCreateResponse:
    secret_plain = generate_secret()                      # Raw secret to return
    secret_encrypt = encrypt_secret(secret_plain)         # Encrypted for DB storage

    async with run_in_transaction() as session:
        new_secret = await create_user_secret(
            db=session,
            user_id=user_id,
            secret=secret_encrypt,
            label=payload.label,
            is_active=payload.is_active if payload.is_active is not None else True,
            expires_at=payload.expires_at or datetime.now(timezone.utc).replace(year=datetime.now().year + 1)
        )

        logger.info("[SECRET] Created new secret | user_id=%s | label=%s | active=%s", user_id, new_secret.label, new_secret.is_active)

    return SecretCreateResponse(label=new_secret.label, secret=secret_plain)


# Deletes a specific secret by label for the given user.
# If the label doesn't exist, raises a validation error.
async def delete_secret_by_label(user_id: UUID, label: str) -> str:
    async with run_in_transaction() as session:
        deleted = await delete_user_secret_by_label(session, user_id, label)
        if not deleted:
            logger.warning("[SECRET] Delete failed | user_id=%s | label=%s", user_id, label)
            raise AuthValidationError(f"Secret with label '{label}' not found.")
        logger.info("[SECRET] Deleted secret | user_id=%s | label=%s", user_id, label)
    return label


# Enables or disables a secret by updating its `is_active` flag.
# Will raise error if secret with that label doesn't exist or is already in desired state.
async def set_secret_active_status(user_id: UUID, label: str, is_active: bool) -> str:
    async with run_in_transaction() as session:
        updated = await set_user_secret_active_status(session, user_id, label, is_active)
        if not updated:
            logger.warning("[SECRET] Toggle failed | user_id=%s | label=%s | desired_state=%s", user_id, label, is_active)
            raise AuthValidationError(f"Secret with label '{label}' not found or already in desired state.")
        logger.info("[SECRET] Set active status | user_id=%s | label=%s | active=%s", user_id, label, is_active)
    return label
