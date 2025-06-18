from typing import List
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.DB_tables.webhook import Webhook

async def get_webhooks_by_user(session: AsyncSession, user_id: UUID) -> List[Webhook]:
    result = await session.execute(
        select(Webhook).where(Webhook.user_id == user_id)
    )
    return list(result.scalars().all())

async def get_webhooks_by_user_and_event(session: AsyncSession, user_id: UUID, event_type: str) -> List[Webhook]:
    result = await session.execute(
        select(Webhook).where(
            Webhook.user_id == user_id,
            Webhook.event_type == event_type
        )
    )
    return list(result.scalars().all())

async def get_active_webhooks_by_event(session: AsyncSession, event_type: str) -> List[Webhook]:
    result = await session.execute(
        select(Webhook).where(
            (Webhook.event_type == event_type) | (Webhook.event_type == "*"),
            Webhook.enabled == True
        )
    )
    return list(result.scalars().all())

async def get_webhook_by_id_and_user(session: AsyncSession, webhook_id: UUID, user_id: UUID) -> Webhook | None:
    result = await session.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.user_id == user_id
        )
    )
    return result.scalar_one_or_none()

async def create_webhook(session: AsyncSession, webhook: Webhook) -> Webhook:
    session.add(webhook)
    await session.flush()
    return webhook

async def update_webhook(session: AsyncSession, webhook: Webhook) -> Webhook:
    session.add(webhook)
    await session.flush()
    return webhook

async def delete_webhook(session: AsyncSession, webhook_id: UUID, user_id: UUID) -> bool:
    result = await session.execute(
        delete(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.user_id == user_id
        )
    )
    return result.rowcount > 0
