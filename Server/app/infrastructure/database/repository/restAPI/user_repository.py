from collections.abc import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update
from app.models.DB_tables.user import User
from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.utils.exceptions_base import AppException


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """
    Fetch a user by their email address.

    Returns:
        User | None: Matching user or None.

    Raises:
        AppException: On DB error.
    """
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


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """
    Fetch a user by UUID.

    Returns:
        User | None: The user or None.

    Raises:
        AppException: On DB error.
    """
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


async def get_all_users(session: AsyncSession) -> Sequence[User]:
    """
    List all registered users.

    Returns:
        Sequence[User]: All user records.

    Raises:
        AppException: On DB failure.
    """
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


async def create_user(
    session: AsyncSession,
    email: str,
    username: str,
    hashed_password: str,
    role: str = "authenticated",
) -> User:
    """
    Register a new user.

    Args:
        email: Unique email address.
        username: User display name.
        hashed_password: Secure password hash.
        role: User role (default: 'authenticated').

    Returns:
        User: Created user object.

    Raises:
        AppException: On DB write failure.
    """
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


async def update_last_login(session: AsyncSession, user_id: UUID):
    """
    Record the current time as the user's last login.

    Raises:
        AppException: On DB failure.
    """
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


async def update_user_secret_ref(db: AsyncSession, user_id: UUID, secret_id: UUID) -> None:
    """
    Update a user's currently active secret ID.

    Raises:
        AppException: On DB update error.
    """
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


async def update_user_password(session: AsyncSession, user_id: UUID, hashed_password: str):
    """
    Change the password hash for a user.

    Raises:
        AppException: On DB failure.
    """
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


async def delete_user(session: AsyncSession, user_id: UUID) -> None:
    """
    Permanently delete a user by ID.

    Raises:
        AppException: On DB failure.
    """
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
