from collections.abc import Sequence
from typing import Optional
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.models.DB_tables.user_secrets import UserSecret
from app.utils.exceptions_base import AppException


async def create_user_secret(
    db: AsyncSession,
    user_id,
    secret: str,
    label: str,
    is_active: bool,
    expires_at: datetime,
) -> UserSecret:
    try:
        new_secret = UserSecret(
            id=uuid4(),
            user_id=user_id,
            secret=secret,
            label=label,
            is_active=is_active,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            revoked_at=None
        )

        db.add(new_secret)
        await db.flush()
        return new_secret
    except Exception as e:
        raise AppException(
            message=f"Failed to create secret for user {user_id}: {e}",
            status_code=500,
            public_message="Failed to create user secret.",
            domain="auth"
        )


async def get_all_active_user_secrets(db: AsyncSession, user_id: UUID) -> Sequence[UserSecret]:
    try:
        result = await db.execute(
            select(UserSecret).where(
                UserSecret.user_id == user_id,
                UserSecret.is_active.is_(True)
            )
        )
        return list(result.scalars().all())
    except Exception as e:
        raise AppException(
            message=f"Failed to get active secrets for user {user_id}: {e}",
            status_code=500,
            public_message="Could not retrieve user secrets.",
            domain="auth"
        )


async def revoke_all_user_secrets(session: AsyncSession, user_id: UUID):
    try:
        await session.execute(
            update(UserSecret)
            .where(UserSecret.user_id == user_id, UserSecret.is_active == True)
            .values(is_active=False, revoked_at=datetime.now(timezone.utc))
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to revoke secrets for user {user_id}: {e}",
            status_code=500,
            public_message="Could not revoke user secrets.",
            domain="auth"
        )


async def get_user_secrets(session: AsyncSession, user_id: UUID) -> list[UserSecret]:
    try:
        result = await session.execute(
            select(UserSecret).where(UserSecret.user_id == user_id)
        )
        return list(result.scalars().all())
    except Exception as e:
        raise AppException(
            message=f"Failed to get all secrets for user {user_id}: {e}",
            status_code=500,
            public_message="Could not retrieve user secrets.",
            domain="auth"
        )


async def delete_user_secrets(session: AsyncSession, user_id: UUID) -> None:
    try:
        await session.execute(
            delete(UserSecret).where(UserSecret.user_id == user_id)
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to delete secrets for user {user_id}: {e}",
            status_code=500,
            public_message="Failed to delete user secrets.",
            domain="auth"
        )


async def get_user_secret_by_label(
    session: AsyncSession,
    user_id: UUID,
    label: str
) -> UserSecret | None:
    try:
        result = await session.execute(
            select(UserSecret).where(
                UserSecret.user_id == user_id,
                UserSecret.label == label
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        raise AppException(
            message=f"Failed to fetch secret by label '{label}' for user {user_id}: {e}",
            status_code=500,
            public_message="Could not find the requested secret.",
            domain="auth"
        )

async def get_user_secret_labels(
    session: AsyncSession,
    user_id: UUID,
    is_active: Optional[bool] = None
) -> list[str]:
    try:
        stmt = select(UserSecret.label).where(UserSecret.user_id == user_id)

        # Only apply is_active filter if explicitly passed
        if isinstance(is_active, bool):
            stmt = stmt.where(UserSecret.is_active.is_(is_active))

        result = await session.execute(stmt)
        return [row[0] for row in result.all()]

    except Exception as e:
        raise AppException(
            message=f"Failed to fetch secret labels for user {user_id}: {e}",
            status_code=500,
            public_message="Could not retrieve secret labels.",
            domain="auth"
        )

async def delete_user_secret_by_label(session: AsyncSession, user_id: UUID, label: str) -> bool:
    result = await session.execute(
        delete(UserSecret).where(
            UserSecret.user_id == user_id,
            UserSecret.label == label
        )
    )
    return result.rowcount > 0

async def set_user_secret_active_status(
    session: AsyncSession,
    user_id: UUID,
    label: str,
    is_active: bool
) -> bool:
    result = await session.execute(
        update(UserSecret)
        .where(
            UserSecret.user_id == user_id,
            UserSecret.label == label,
            UserSecret.is_active.isnot(is_active)
        )
        .values(
            is_active=is_active,
            revoked_at=(datetime.now(timezone.utc) if not is_active else None)
        )
    )
    return result.rowcount > 0



async def get_user_secrets_info(
    session: AsyncSession,
    user_id: UUID,
    is_active: Optional[bool] = None
) -> list[dict]:
    try:
        stmt = select(
            UserSecret.label,
            UserSecret.is_active,
            UserSecret.created_at,
            UserSecret.expires_at
        ).where(UserSecret.user_id == user_id)

        if isinstance(is_active, bool):
            stmt = stmt.where(UserSecret.is_active.is_(is_active))

        result = await session.execute(stmt)
        return [
            {
                "label": row[0],
                "is_active": row[1],
                "created_at": row[2],
                "expires_at": row[3]
            }
            for row in result.all()
        ]

    except Exception as e:
        raise AppException(
            message=f"Failed to fetch secret info for user {user_id}: {e}",
            status_code=500,
            public_message="Could not retrieve secret info.",
            domain="auth"
        )