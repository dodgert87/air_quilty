from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, update
from app.models.api_keys import APIKey
from sqlalchemy.ext.asyncio import AsyncSession


async def create_api_key( session: AsyncSession, user_id: UUID, key: str, label: str | None = None, expires_at: datetime | None = None) -> APIKey:
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

async def delete_api_key_by_label(session: AsyncSession, user_id: UUID, label: str) -> bool:
    result = await session.execute(
        delete(APIKey)
        .where(APIKey.user_id == user_id, APIKey.label == label)
        .returning(APIKey.label)
    )
    deleted_label = result.scalar_one_or_none()
    return deleted_label is not None

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

async def revoke_all_user_api_keys(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        update(APIKey)
        .where(APIKey.user_id == user_id, APIKey.is_active.is_(True))
        .values(is_active=False)
    )


async def delete_all_user_api_keys(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        delete(APIKey).where(APIKey.user_id == user_id)
    )