from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from app.models.api_keys import APIKey
from sqlalchemy.ext.asyncio import AsyncSession


async def create_api_key(session: AsyncSession, user_id: UUID, key: str, label: str | None = None) -> APIKey:
    new_key = APIKey(
        key=key,
        user_id=user_id,
        label=label,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    session.add(new_key)
    return new_key

async def get_api_keys_by_user(session: AsyncSession, user_id: UUID) -> Sequence[APIKey]:
    result = await session.execute(
        select(APIKey).where(APIKey.user_id == user_id)
    )
    return result.scalars().all()

async def get_active_api_key(session: AsyncSession, key: str) -> APIKey | None:
    result = await session.execute(
        select(APIKey).where(APIKey.key == key, APIKey.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def get_all_active_keys(session: AsyncSession) -> list[APIKey]:
    result = await session.execute(
        select(APIKey).where(APIKey.is_active.is_(True))
    )
    return list(result.scalars().all())