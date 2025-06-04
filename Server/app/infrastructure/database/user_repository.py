from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from uuid import UUID, uuid4
from datetime import datetime, timezone


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """
    Returns a user object by email, or None if not found.
    """
    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    username: str,
    hashed_password: str,
    role: str = "authenticated",
) -> User:
    """
    Creates a new user record in the database.
    """
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


async def update_user_secret_ref(
    db: AsyncSession,
    user_id: UUID,
    secret_id: UUID
) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(active_secret_id=secret_id)
    )
    await db.flush()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()