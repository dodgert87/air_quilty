from uuid import UUID
import hmac
import hashlib
import json
import httpx
from loguru import logger
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repository.restAPI.secret_repository import update_webhook_retry
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.utils.config import settings


async def send_webhook(session: AsyncSession, webhook: WebhookConfig, payload: dict | BaseModel) -> None:
    """
    Send a signed JSON POST request to a webhook target.

    Uses HMAC-SHA256 with the user-defined secret to generate a signature,
    retries on 5xx server errors, and logs all outcomes.

    Args:
        session (AsyncSession): DB session for logging retry status if needed.
        webhook (WebhookConfig): Config object containing target URL, headers, and secret.
        payload (dict | BaseModel): The payload to send.

    Raises:
        None directly. Logs all exceptions and saves failure state.
    """
    # ─── Serialize Payload ─────────────────────────────
    if isinstance(payload, BaseModel):
        payload_json = payload.model_dump_json()
    else:
        payload_json = json.dumps(payload, default=fallback_serializer, separators=(",", ":"), sort_keys=True)

    # ─── Generate HMAC-SHA256 Signature ───────────────
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

    # ─── Attempt Delivery with Retry ───────────────────
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
                # Retryable server error
                last_error = f"HTTP {status}: {response.text}"
                logger.warning("[WEBHOOK] Server error | id=%s | attempt=%d | error=%s", webhook.id, attempt + 1, last_error)

            else:
                # Client error or other non-retryable status
                logger.error("[WEBHOOK] Permanent failure | id=%s | status=%d | response=%s", webhook.id, status, response.text)
                return

        except Exception as e:
            # Network or unexpected exception
            last_error = str(e)
            logger.warning("[WEBHOOK] Network/Send error | id=%s | attempt=%d | error=%s", webhook.id, attempt + 1, last_error)

    # ─── Final Failure: Log & Persist Error ────────────
    logger.error("[WEBHOOK] Failed after %d attempts | id=%s | last_error=%s", max_attempts, webhook.id, last_error)
    await update_webhook_retry(session, webhook.id, last_error=last_error)



def fallback_serializer(obj):
    """
    Fallback serializer for UUIDs and datetime objects when encoding raw dict payloads to JSON.

    Args:
        obj (Any): Object to serialize.

    Returns:
        str: Serialized representation.

    Raises:
        TypeError: If object type is unsupported.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
