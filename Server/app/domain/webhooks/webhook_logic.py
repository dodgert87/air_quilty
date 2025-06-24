from uuid import UUID
from typing import List, Optional
import hmac
import hashlib
import json
import httpx
from loguru import logger
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.crypto_utils import decrypt_secret
from app.models.DB_tables.user_secrets import UserSecret
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
    try:
        async with run_in_transaction() as session:
            webhooks = await get_webhooks_by_user(session, user_id)
            logger.info("[WEBHOOK] Fetched user webhooks | user_id=%s | count=%d", user_id, len(webhooks))
            return webhooks
    except Exception as e:
        logger.exception("[WEBHOOK] Failed to fetch user webhooks | user_id=%s", user_id)
        raise AppException.from_internal_error("Unable to retrieve webhooks", domain="webhook")


async def get_allowed_events_for_role(role: str) -> List[str]:
    events = ROLE_TO_WEBHOOK_EVENTS.get(role, [])
    logger.info("[WEBHOOK] Allowed events for role | role=%s | events=%s", role, events)
    return events


async def create_webhook(user_id: UUID, user_role: str, data: WebhookCreate) -> Webhook:
    async with run_in_transaction() as session:
        if data.event_type not in ROLE_TO_WEBHOOK_EVENTS.get(user_role, []):
            logger.warning("[WEBHOOK] Unauthorized event | user=%s | role=%s | event=%s", user_id, user_role, data.event_type)
            raise AppException(
                message=f"Unauthorized event_type '{data.event_type}' for role '{user_role}'",
                status_code=403,
                public_message="This event is not allowed for your role.",
                domain="webhook"
            )

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

        if secret_id and data.secret_label:
            secret_obj = await get_user_secret_by_label(session, user_id, data.secret_label)
            if not secret_obj:
                logger.error("[WEBHOOK] Secret not found after creation | label=%s", data.secret_label)
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
    async with run_in_transaction() as session:
        webhook = await get_webhook_by_id_and_user(session, webhook_id, user_id)
        event_type = webhook.event_type if webhook else None

        deleted = await delete_webhook_in_db(session, webhook_id, user_id)

        if deleted and event_type:
            dispatcher.remove_from_registry(webhook_id, WebhookEvent(event_type))
            logger.info("[WEBHOOK] Deleted webhook | id=%s | user=%s", webhook_id, user_id)

        if not deleted:
            logger.warning("[WEBHOOK] Webhook not found for deletion | id=%s | user=%s", webhook_id, user_id)
            raise AppException(
                message=f"Webhook {webhook_id} not found for user {user_id}",
                status_code=404,
                public_message="Webhook not found.",
                domain="webhook"
            )
        return True


async def update_webhook(user_id: UUID, payload: WebhookUpdatePayload) -> Webhook:
    async with run_in_transaction() as session:
        webhook = await get_webhook_by_id_and_user(session, payload.webhook_id, user_id)
        if not webhook:
            logger.warning("[WEBHOOK] Webhook not found for update | id=%s | user=%s", payload.webhook_id, user_id)
            raise AppException(
                message=f"Webhook {payload.webhook_id} not found for user {user_id}",
                status_code=404,
                public_message="Webhook not found or not yours.",
                domain="webhook"
            )

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

        if payload.secret_label:
            secret = await get_user_secret_by_label(session, user_id, payload.secret_label)
            if not secret or not secret.is_active or secret.revoked_at:
                logger.warning("[WEBHOOK] Invalid secret on update | user=%s | label=%s", user_id, payload.secret_label)
                raise AppException(
                    message=f"Invalid or inactive secret '{payload.secret_label}'",
                    status_code=403,
                    public_message="Secret is invalid or inactive.",
                    domain="webhook"
                )
            webhook.secret_id = secret.id

        updated = await update_webhook_in_db(session, webhook)
        logger.info("[WEBHOOK] Updated webhook | id=%s | user=%s", updated.id, user_id)

        if webhook.secret_id:
            secret_obj = await get_user_secret_by_id(session, webhook.secret_id)
            if not secret_obj:
                logger.error("[WEBHOOK] Secret not found after update | id=%s", webhook.secret_id)
                raise AppException(
                    message="Secret not found",
                    status_code=404,
                    public_message="Webhook secret not found.",
                    domain="webhook"
                )

            config = WebhookConfig.from_orm_and_secret(updated, decrypt_secret(secret_obj.secret))
            dispatcher.replace_in_registry(config)

        return updated



