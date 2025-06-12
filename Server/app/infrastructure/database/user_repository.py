from collections.abc import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update
from app.models.user import User
from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.utils.exceptions_base import AppException


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    try:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        raise AppException(
            message=f"Failed to fetch user by email '{email}': {e}",
            status_code=500,
            public_message="Could not fetch user by email.",
            domain="auth"
        )


async def create_user(
    session: AsyncSession,
    email: str,
    username: str,
    hashed_password: str,
    role: str = "authenticated",
) -> User:
    try:
        new_user = User(
            id=uuid4(),
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=role,
            created_at=datetime.now(timezone.utc),
            last_login=None,
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user
    except Exception as e:
        raise AppException(
            message=f"Failed to create user {email}: {e}",
            status_code=500,
            public_message="Could not create user.",
            domain="auth"
        )


async def update_user_secret_ref(
    db: AsyncSession,
    user_id: UUID,
    secret_id: UUID
) -> None:
    try:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(active_secret_id=secret_id)
        )
        await db.flush()
    except Exception as e:
        raise AppException(
            message=f"Failed to update active secret for user {user_id}: {e}",
            status_code=500,
            public_message="Could not update user's secret reference.",
            domain="auth"
        )


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        raise AppException(
            message=f"Failed to fetch user by ID {user_id}: {e}",
            status_code=500,
            public_message="Could not fetch user by ID.",
            domain="auth"
        )


async def update_user_password(session: AsyncSession, user_id: UUID, hashed_password: str):
    try:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to update password for user {user_id}: {e}",
            status_code=500,
            public_message="Could not update password.",
            domain="auth"
        )


async def update_last_login(session: AsyncSession, user_id: UUID):
    try:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to update last login for user {user_id}: {e}",
            status_code=500,
            public_message="Could not update last login.",
            domain="auth"
        )


async def delete_user(session: AsyncSession, user_id: UUID) -> None:
    try:
        await session.execute(
            delete(User).where(User.id == user_id)
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to delete user {user_id}: {e}",
            status_code=500,
            public_message="Could not delete user.",
            domain="auth"
        )


async def get_all_users(session: AsyncSession) -> Sequence[User]:
    try:
        result = await session.execute(select(User))
        return result.scalars().all()
    except Exception as e:
        raise AppException(
            message=f"Failed to list all users: {e}",
            status_code=500,
            public_message="Could not retrieve users.",
            domain="auth"
        )
