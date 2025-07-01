from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.DB_tables.api_keys import APIKey
from app.utils.exceptions_base import AppException


# ──────────────────────────────── CREATE ────────────────────────────────

async def create_api_key(
    session: AsyncSession,
    user_id: UUID,
    key: str,
    label: str | None = None,
    expires_at: datetime | None = None
) -> APIKey:
    """
    Create a new API key for the given user.

    Args:
        session (AsyncSession): SQLAlchemy async session.
        user_id (UUID): Owner of the key.
        key (str): Hashed key to store.
        label (str | None): Optional label for human reference.
        expires_at (datetime | None): Optional expiration timestamp.

    Returns:
        APIKey: Newly created APIKey record.

    Raises:
        AppException: On creation failure.
    """
    try:
        new_key = APIKey(
            key=key,
            user_id=user_id,
            label=label,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        session.add(new_key)
        return new_key
    except Exception as e:
        raise AppException(
            message=f"Failed to create API key for user {user_id}: {e}",
            status_code=500,
            public_message="Failed to create API key.",
            domain="auth"
        )


# ──────────────────────────────── DELETE ────────────────────────────────

async def delete_api_key_by_label(session: AsyncSession, user_id: UUID, label: str) -> str | None:
    """
    Delete a specific API key by its label for a given user.

    Returns:
        str | None: Deleted key string, or None if not found.

    Raises:
        AppException: On deletion error.
    """
    try:
        result = await session.execute(
            delete(APIKey)
            .where(APIKey.user_id == user_id, APIKey.label == label)
            .returning(APIKey.key)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        raise AppException(
            message=f"Failed to delete API key with label '{label}' for user {user_id}: {e}",
            status_code=500,
            public_message="Failed to delete API key.",
            domain="auth"
        )


async def delete_all_user_api_keys(session: AsyncSession, user_id: UUID) -> None:
    """
    Delete all API keys belonging to a specific user.

    Raises:
        AppException: On deletion failure.
    """
    try:
        await session.execute(
            delete(APIKey).where(APIKey.user_id == user_id)
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to delete all API keys for user {user_id}: {e}",
            status_code=500,
            public_message="Failed to delete user API keys.",
            domain="auth"
        )


# ──────────────────────────────── RETRIEVE ────────────────────────────────

async def get_api_keys_by_user(session: AsyncSession, user_id: UUID) -> Sequence[APIKey]:
    """
    Get all API keys for a given user.

    Returns:
        Sequence[APIKey]: List of API key records.

    Raises:
        AppException: On query failure.
    """
    try:
        result = await session.execute(
            select(APIKey).where(APIKey.user_id == user_id)
        )
        return result.scalars().all()
    except Exception as e:
        raise AppException(
            message=f"Failed to retrieve API keys for user {user_id}: {e}",
            status_code=500,
            public_message="Failed to fetch API keys.",
            domain="auth"
        )


async def get_active_api_key(session: AsyncSession, key: str) -> APIKey | None:
    """
    Retrieve an active API key by its key string.

    Returns:
        APIKey | None: Active APIKey record or None.

    Raises:
        AppException: On query failure.
    """
    try:
        result = await session.execute(
            select(APIKey).where(APIKey.key == key, APIKey.is_active.is_(True))
        )
        return result.scalar_one_or_none()
    except Exception as e:
        raise AppException(
            message=f"Failed to get active API key: {e}",
            status_code=500,
            public_message="Failed to validate API key.",
            domain="auth"
        )


async def get_all_active_keys(session: AsyncSession) -> list[APIKey]:
    """
    List all active API keys in the system.

    Returns:
        list[APIKey]: List of active keys.

    Raises:
        AppException: On retrieval failure.
    """
    try:
        result = await session.execute(
            select(APIKey).where(APIKey.is_active.is_(True))
        )
        return list(result.scalars().all())
    except Exception as e:
        raise AppException(
            message=f"Failed to list all active API keys: {e}",
            status_code=500,
            public_message="Failed to fetch active API keys.",
            domain="auth"
        )


# ──────────────────────────────── REVOKE ────────────────────────────────

async def revoke_all_user_api_keys(session: AsyncSession, user_id: UUID) -> None:
    """
    Mark all API keys of a user as inactive (revoked).

    Raises:
        AppException: On update failure.
    """
    try:
        await session.execute(
            update(APIKey)
            .where(APIKey.user_id == user_id, APIKey.is_active.is_(True))
            .values(is_active=False)
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to revoke API keys for user {user_id}: {e}",
            status_code=500,
            public_message="Failed to revoke API keys.",
            domain="auth"
        )
