from uuid import UUID
from typing import List
from loguru import logger
from app.utils.crypto_utils import decrypt_secret
from app.infrastructure.database.transaction import run_in_transaction
from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_id, get_user_secret_by_label, update_webhook_retry
from app.infrastructure.database.repository.webhook.webhook_repository import (
    get_webhooks_by_user,
    get_webhook_by_id_and_user,
    create_webhook as create_webhook_in_db,
    update_webhook as update_webhook_in_db,
    delete_webhook as delete_webhook_in_db,
)
from app.constants.webhooks import ROLE_TO_WEBHOOK_EVENTS, WebhookEvent
from app.models.schemas.webhook.webhook_schema import WebhookConfig, WebhookCreate, WebhookUpdatePayload
from app.models.DB_tables.webhook import Webhook
from app.utils.exceptions_base import AppException
from app.utils.config import settings
from app.domain.webhooks.dispatcher import dispatcher



async def get_user_webhooks(user_id: UUID) -> List[Webhook]:
    """
    Fetch all webhook records owned by the user.

    Args:
        user_id: UUID of the user.

    Returns:
        List[Webhook]: Webhook DB entries.
    """
    try:
        async with run_in_transaction() as session:
            webhooks = await get_webhooks_by_user(session, user_id)
            logger.info("[WEBHOOK] Fetched user webhooks | user_id=%s | count=%d", user_id, len(webhooks))
            return webhooks
    except Exception as e:
        logger.exception("[WEBHOOK] Failed to fetch user webhooks | user_id=%s", user_id)
        raise AppException.from_internal_error("Unable to retrieve webhooks", domain="webhook")



async def get_allowed_events_for_role(role: str) -> List[str]:
    """
    Returns the list of allowed webhook events for a given user role.

    Args:
        role: Role of the user.

    Returns:
        List[str]: Event names the user can subscribe to.
    """
    events = ROLE_TO_WEBHOOK_EVENTS.get(role, [])
    logger.info("[WEBHOOK] Allowed events for role | role=%s | events=%s", role, events)
    return events



async def create_webhook(user_id: UUID, user_role: str, data: WebhookCreate) -> Webhook:
    """
    Create a webhook entry for the user and register it with the dispatcher.

    Performs:
    - Role-based event type restriction
    - Secret label validation and lookup
    - DB insertion + dispatcher sync

    Raises:
        AppException: If unauthorized, invalid secret, or DB fails.
    """
    async with run_in_transaction() as session:
        # ─── Check permission ───
        if data.event_type not in ROLE_TO_WEBHOOK_EVENTS.get(user_role, []):
            logger.warning("[WEBHOOK] Unauthorized event | user=%s | role=%s | event=%s", user_id, user_role, data.event_type)
            raise AppException(
                message=f"Unauthorized event_type '{data.event_type}' for role '{user_role}'",
                status_code=403,
                public_message="This event is not allowed for your role.",
                domain="webhook"
            )

        # ─── Validate secret (optional) ───
        secret_id: UUID | None = None
        if data.secret_label:
            secret = await get_user_secret_by_label(session, user_id, data.secret_label)
            if not secret or not secret.is_active or secret.revoked_at:
                logger.warning("[WEBHOOK] Invalid secret | user=%s | label=%s", user_id, data.secret_label)
                raise AppException(
                    message=f"Invalid or inactive secret '{data.secret_label}'",
                    status_code=403,
                    public_message="Secret is invalid or inactive.",
                    domain="webhook"
                )
            secret_id = secret.id

        # ─── Build & store DB object ───
        webhook = Webhook(
            user_id=user_id,
            event_type=data.event_type,
            target_url=str(data.target_url),
            secret_id=secret_id,
            custom_headers=data.custom_headers or {},
            parameters=data.parameters,
        )
        created = await create_webhook_in_db(session, webhook)
        logger.info("[WEBHOOK] Created webhook | id=%s | user=%s", created.id, user_id)

        # ─── Register in dispatcher ───
        if secret_id and data.secret_label:
            secret_obj = await get_user_secret_by_label(session, user_id, data.secret_label)
            if not secret_obj:
                raise AppException(
                    message="Secret not found",
                    status_code=404,
                    public_message="Webhook secret not found.",
                    domain="webhook"
                )
            config = WebhookConfig.from_orm_and_secret(created, decrypt_secret(secret_obj.secret))
            dispatcher.add_to_registry(config)

        return created



async def delete_webhook(user_id: UUID, webhook_id: UUID) -> bool:
    """
    Delete a user's webhook and unregister it from the dispatcher.

    Raises:
        AppException: If webhook not found or unauthorized.
    """
    async with run_in_transaction() as session:
        webhook = await get_webhook_by_id_and_user(session, webhook_id, user_id)
        event_type = webhook.event_type if webhook else None

        deleted = await delete_webhook_in_db(session, webhook_id, user_id)

        if deleted and event_type:
            dispatcher.remove_from_registry(webhook_id, WebhookEvent(event_type))
            logger.info("[WEBHOOK] Deleted webhook | id=%s | user=%s", webhook_id, user_id)

        if not deleted:
            raise AppException(
                message=f"Webhook {webhook_id} not found for user {user_id}",
                status_code=404,
                public_message="Webhook not found.",
                domain="webhook"
            )
        return True



async def update_webhook(user_id: UUID, payload: WebhookUpdatePayload) -> Webhook:
    """
    Update an existing webhook’s metadata and re-register it with the dispatcher.

    Supports partial updates:
    - Target URL
    - Enabled flag
    - Custom headers
    - Event type
    - Parameters
    - Secret reference (by label)

    Raises:
        AppException: On not found, invalid secret, or DB failure.
    """
    async with run_in_transaction() as session:
        webhook = await get_webhook_by_id_and_user(session, payload.webhook_id, user_id)
        if not webhook:
            raise AppException(
                message=f"Webhook {payload.webhook_id} not found for user {user_id}",
                status_code=404,
                public_message="Webhook not found or not yours.",
                domain="webhook"
            )

        # ─── Apply field updates ───
        if payload.target_url is not None:
            webhook.target_url = str(payload.target_url)
        if payload.event_type is not None:
            webhook.event_type = payload.event_type
        if payload.enabled is not None:
            webhook.enabled = payload.enabled
        if payload.custom_headers is not None:
            webhook.custom_headers = payload.custom_headers
        if payload.parameters is not None:
            webhook.parameters = payload.parameters

        # ─── Update secret reference ───
        if payload.secret_label:
            secret = await get_user_secret_by_label(session, user_id, payload.secret_label)
            if not secret or not secret.is_active or secret.revoked_at:
                raise AppException(
                    message=f"Invalid or inactive secret '{payload.secret_label}'",
                    status_code=403,
                    public_message="Secret is invalid or inactive.",
                    domain="webhook"
                )
            webhook.secret_id = secret.id

        # ─── Save and re-register ───
        updated = await update_webhook_in_db(session, webhook)
        logger.info("[WEBHOOK] Updated webhook | id=%s | user=%s", updated.id, user_id)

        if webhook.secret_id:
            secret_obj = await get_user_secret_by_id(session, webhook.secret_id)
            if not secret_obj:
                raise AppException(
                    message="Secret not found",
                    status_code=404,
                    public_message="Webhook secret not found.",
                    domain="webhook"
                )
            config = WebhookConfig.from_orm_and_secret(updated, decrypt_secret(secret_obj.secret))
            dispatcher.replace_in_registry(config)

        return updated


