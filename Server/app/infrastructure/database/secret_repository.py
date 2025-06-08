from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.models.user_secrets import UserSecret

async def create_user_secret(
    db: AsyncSession,
    user_id,
    secret: str,
    label: str,
    is_active: bool,
    expires_at: datetime,
) -> UserSecret:
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


async def get_all_active_user_secrets(db: AsyncSession, user_id: UUID) -> Sequence[UserSecret]:
    result = await db.execute(
        select(UserSecret).where(
            UserSecret.user_id == user_id,
            UserSecret.is_active.is_(True)
        )
    )
    return list(result.scalars().all())