from uuid import UUID
import hmac
import hashlib
import json
import httpx
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repository.restAPI.secret_repository import  update_webhook_retry
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.utils.config import settings




async def send_webhook(session: AsyncSession, webhook: WebhookConfig, payload: dict | BaseModel) -> None:
    #print(f"Sending webhook {webhook.id} to {webhook.target_url} with payload: {payload}")

    # JSON payload serialization
    if isinstance(payload, BaseModel):
        payload_json = payload.model_dump_json()
    else:
        payload_json = json.dumps(payload, default=fallback_serializer, separators=(",", ":"), sort_keys=True)

    # Signature generation
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

    # Retry mechanism
    max_attempts = settings.MAX_ATTEMPTS_PER_WEBHOOK
    last_error = None


    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, verify=True) as client:
                response = await client.post(str(webhook.target_url), content=payload_json, headers=headers)

            status = response.status_code

            if 200 <= status < 300:
                print(f"Webhook {webhook.id} sent successfully on attempt {attempt + 1}")
                return

            elif 500 <= status < 600:
                last_error = f"HTTP {status}: {response.text}"

            else:
                print(f"Webhook {webhook.id} failed permanently with status {status}: {response.text}")
                return

        except Exception as e:
            last_error = str(e)

    print(f"Webhook {webhook.id} failed after {max_attempts} attempts. Last error: {last_error}")
    await update_webhook_retry(session, webhook.id, last_error=last_error)

# fallback for dicts (e.g., if dispatcher accepted a raw dict)

def fallback_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")