from uuid import UUID
from typing import List, Optional
import hmac
import hashlib
import json
import httpx
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
from app.constants.webhooks import ROLE_TO_WEBHOOK_EVENTS
from app.models.schemas.webhook.webhook_schema import WebhookCreate, WebhookUpdatePayload
from app.models.DB_tables.webhook import Webhook
from app.utils.exceptions_base import AppException
from app.utils.config import settings



async def get_user_webhooks(user_id: UUID) -> List[Webhook]:
    async with run_in_transaction() as session:
        return await get_webhooks_by_user(session, user_id)


async def get_allowed_events_for_role(role: str) -> List[str]:
    return ROLE_TO_WEBHOOK_EVENTS.get(role, [])


async def create_webhook(user_id: UUID, user_role: str, data: WebhookCreate) -> Webhook:
    async with run_in_transaction() as session:
        if data.event_type not in ROLE_TO_WEBHOOK_EVENTS.get(user_role, []):
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
        )

        return await create_webhook_in_db(session, webhook)


async def delete_webhook(user_id: UUID, webhook_id: UUID) -> bool:
    async with run_in_transaction() as session:
        deleted = await delete_webhook_in_db(session, webhook_id, user_id)
        if not deleted:
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

        return await update_webhook_in_db(session, webhook)


async def send_webhook(session: AsyncSession, webhook: Webhook, payload: dict) -> None:
    print(f"Sending webhook {webhook.id} to {webhook.target_url} with payload: {payload}")
    if not webhook.enabled:
        return

    if not webhook.secret_id:
        raise ValueError("Webhook has no associated secret. Cannot sign payload.")

    secret_obj: Optional[UserSecret] = await get_user_secret_by_id(session, webhook.secret_id)
    if not secret_obj:
        raise ValueError("Secret not found or revoked. Cannot sign webhook.")

    # JSON payload signing
    if isinstance(payload, BaseModel):
        payload_json = payload.model_dump_json()
    else:

        payload_json = json.dumps(payload, default=fallback_serializer, separators=(",", ":"), sort_keys=True)

    raw_secret = decrypt_secret(secret_obj.secret)
    signature = hmac.new(
        raw_secret.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={signature}"
    }

    if webhook.custom_headers:
        headers.update(webhook.custom_headers)

    # Retry mechanism
    max_attempts = settings.MAX_ATTEMPTS_PER_WEBHOOK
    last_error = None


    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, verify=True) as client:
                response = await client.post(webhook.target_url, content=payload_json, headers=headers)

            status = response.status_code

            if 200 <= status < 300:
                print(f"Webhook {webhook.id} sent successfully on attempt {attempt + 1}")
                await update_webhook_retry(session, webhook.id, retry_count=0)
                return

            elif 500 <= status < 600:
                last_error = f"HTTP {status}: {response.text}"

            else:
                print(f"Webhook {webhook.id} failed permanently with status {status}: {response.text}")
                await update_webhook_retry(session, webhook.id, retry_count=0, last_error=f"Client error: {response.text}")
                return

        except Exception as e:
            last_error = str(e)

    await update_webhook_retry(session, webhook.id, retry_count=webhook.retry_count + 1, last_error=last_error)

# fallback for dicts (e.g., if dispatcher accepted a raw dict)

def fallback_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")