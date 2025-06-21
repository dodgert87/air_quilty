
from typing import Any
from app.domain.webhooks.registry.sensor_created_registry import SensorCreatedWebhookRegistry
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.models.schemas.webhook.sensor_created import SensorCreatedPayload
from app.domain.webhooks.handlers.handler_interface import WebhookEventHandler
from app.domain.webhooks.send_webhook import send_webhook
from sqlalchemy.ext.asyncio import AsyncSession

class SensorCreatedHandler(WebhookEventHandler[SensorCreatedPayload]):
    payload_model = SensorCreatedPayload

    async def handle(self, payload: SensorCreatedPayload, session: AsyncSession) -> None:
        payload_dict: dict[str, Any] = payload.model_dump()

        for webhook in SensorCreatedWebhookRegistry.get_all():
            print(f"Dispatching sensor_created webhook to {webhook.target_url} for sensor {payload.sensor_id}")
            await send_webhook(session, webhook, payload_dict)