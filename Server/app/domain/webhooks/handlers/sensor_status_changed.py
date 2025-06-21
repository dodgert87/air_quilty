
from typing import Any
from app.domain.webhooks.registry.sensor_status_registry import SensorStatusWebhookRegistry
from app.constants.webhooks import WebhookEvent
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.models.schemas.rest.sensor_schemas import SensorOut
from app.domain.webhooks.handlers.handler_interface import WebhookEventHandler
from app.domain.webhooks.send_webhook import send_webhook
from sqlalchemy.ext.asyncio import AsyncSession


class SensorStatusChangedHandler(WebhookEventHandler[SensorOut]):
    payload_model = SensorOut

    async def handle(self, payload: SensorOut, session: AsyncSession) -> None:
        payload_dict: dict[str, Any] = payload.model_dump()

        for webhook in SensorStatusWebhookRegistry.get_all():
            print(f"Dispatching 'sensor_status_changed' to {webhook.target_url}")
            await send_webhook(session, webhook, payload_dict)