from typing import List
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.DB_tables.webhook import Webhook
from app.utils.exceptions_base import AppException
from loguru import logger

async def get_webhooks_by_user(session: AsyncSession, user_id: UUID) -> List[Webhook]:
    """
    Return all webhooks registered by a specific user.
    """
    result = await session.execute(
        select(Webhook).where(Webhook.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_webhooks_by_user_and_event(session: AsyncSession, user_id: UUID, event_type: str) -> List[Webhook]:
    """
    Return user webhooks filtered by event type.
    """
    result = await session.execute(
        select(Webhook).where(
            Webhook.user_id == user_id,
            Webhook.event_type == event_type
        )
    )
    return list(result.scalars().all())


async def get_active_webhooks_by_event(session: AsyncSession, event_type: str) -> List[Webhook]:
    """
    Fetch all enabled webhooks listening to a specific event.

    Includes wildcards: `event_type == '*'` will match all events.
    """
    result = await session.execute(
        select(Webhook).where(
            (Webhook.event_type == event_type) | (Webhook.event_type == "*"),
            Webhook.enabled == True
        )
    )
    return list(result.scalars().all())


async def get_webhook_by_id_and_user(session: AsyncSession, webhook_id: UUID, user_id: UUID) -> Webhook | None:
    """
    Fetch a specific webhook for a user.

    Returns:
        Webhook | None: Found record or None.
    """
    result = await session.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def create_webhook(session: AsyncSession, webhook: Webhook) -> Webhook:
    """
    Create a new webhook entry.

    Args:
        webhook: Fully constructed Webhook SQLAlchemy object.

    Returns:
        Webhook: Created entry.

    Raises:
        AppException: On DB insert error.
    """
    try:
        session.add(webhook)
        await session.flush()
        logger.info(f"Webhook created: {webhook.id} for user {webhook.user_id}")
        return webhook
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}")
        raise AppException(
            message=f"Failed to create webhook: {e}",
            status_code=500,
            public_message="Webhook creation failed.",
            domain="webhook"
        )


async def update_webhook(session: AsyncSession, webhook: Webhook) -> Webhook:
    """
    Update an existing webhook's values.

    Returns:
        Webhook: Updated webhook.

    Raises:
        AppException: On update failure.
    """
    try:
        session.add(webhook)
        await session.flush()
        logger.info(f"Webhook updated: {webhook.id}")
        return webhook
    except Exception as e:
        logger.error(f"Failed to update webhook {webhook.id}: {e}")
        raise AppException(
            message=f"Failed to update webhook {webhook.id}: {e}",
            status_code=500,
            public_message="Webhook update failed.",
            domain="webhook"
        )


async def delete_webhook(session: AsyncSession, webhook_id: UUID, user_id: UUID) -> bool:
    """
    Delete a webhook owned by a user.

    Returns:
        bool: True if deletion succeeded, False otherwise.

    Raises:
        AppException: On DB error.
    """
    try:
        result = await session.execute(
            delete(Webhook).where(
                Webhook.id == webhook_id,
                Webhook.user_id == user_id
            )
        )
        deleted = result.rowcount > 0
        logger.info(f"Webhook delete for user {user_id}: ID {webhook_id}, success={deleted}")
        return deleted
    except Exception as e:
        logger.error(f"Failed to delete webhook {webhook_id} for user {user_id}: {e}")
        raise AppException(
            message=f"Failed to delete webhook {webhook_id}: {e}",
            status_code=500,
            public_message="Webhook deletion failed.",
            domain="webhook"
        )
