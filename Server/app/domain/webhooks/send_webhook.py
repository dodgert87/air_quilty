from uuid import UUID
import hmac
import hashlib
import json
import httpx
from loguru import logger
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repository.restAPI.secret_repository import  update_webhook_retry
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.utils.config import settings




async def send_webhook(session: AsyncSession, webhook: WebhookConfig, payload: dict | BaseModel) -> None:
    if isinstance(payload, BaseModel):
        payload_json = payload.model_dump_json()
    else:
        payload_json = json.dumps(payload, default=fallback_serializer, separators=(",", ":"), sort_keys=True)

    raw_secret = webhook.secret.get_secret_value()
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

    max_attempts = settings.MAX_ATTEMPTS_PER_WEBHOOK
    last_error = None

    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, verify=True) as client:
                response = await client.post(str(webhook.target_url), content=payload_json, headers=headers)

            status = response.status_code

            if 200 <= status < 300:
                logger.info("[WEBHOOK] Sent successfully | id=%s | url=%s | attempt=%d", webhook.id, webhook.target_url, attempt + 1)
                return

            elif 500 <= status < 600:
                last_error = f"HTTP {status}: {response.text}"
                logger.warning("[WEBHOOK] Server error | id=%s | attempt=%d | error=%s", webhook.id, attempt + 1, last_error)

            else:
                logger.error("[WEBHOOK] Permanent failure | id=%s | status=%d | response=%s", webhook.id, status, response.text)
                return

        except Exception as e:
            last_error = str(e)
            logger.warning("[WEBHOOK] Network/Send error | id=%s | attempt=%d | error=%s", webhook.id, attempt + 1, last_error)

    logger.error("[WEBHOOK] Failed after %d attempts | id=%s | last_error=%s", max_attempts, webhook.id, last_error)
    await update_webhook_retry(session, webhook.id, last_error=last_error)

# fallback for dicts (e.g., if dispatcher accepted a raw dict)

def fallback_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")