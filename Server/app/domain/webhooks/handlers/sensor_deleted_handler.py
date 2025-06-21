from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.webhooks.registry.sensor_deleted_registry import SensorDeletedWebhookRegistry
from app.models.schemas.webhook.webhook_schema import SensorDeletedPayload
from app.domain.webhooks.handlers.handler_interface import WebhookEventHandler
from app.domain.webhooks.send_webhook import send_webhook


class SensorDeletedHandler(WebhookEventHandler[SensorDeletedPayload]):
    payload_model = SensorDeletedPayload

    async def handle(self, payload: SensorDeletedPayload, session: AsyncSession) -> None:
        payload_dict: dict[str, Any] = payload.model_dump()

        for webhook in SensorDeletedWebhookRegistry.get_all():
            print(f"Dispatching 'sensor_deleted' webhook to {webhook.target_url}")
            await send_webhook(session, webhook, payload_dict)
