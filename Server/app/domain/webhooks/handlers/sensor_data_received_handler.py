
from typing import Any
from app.domain.webhooks.registry.sensor_data_received_registry import SensorDataReceivedWebhookRegistry
from app.constants.webhooks import WebhookEvent
from app.models.schemas.rest.sensor_data_schemas import SensorDataOut
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.domain.webhooks.handlers.handler_interface import WebhookEventHandler
from app.domain.webhooks.send_webhook import send_webhook
from sqlalchemy.ext.asyncio import AsyncSession

class SensorDataReceivedHandler(WebhookEventHandler[SensorDataOut]):
    payload_model = SensorDataOut

    async def handle(self, payload: SensorDataOut, session: AsyncSession) -> None:
        payload_dict: dict[str, Any] = payload.model_dump()

        for webhook in SensorDataReceivedWebhookRegistry.get_all():
            print(f"Dispatching 'sensor_data_received' to {webhook.target_url}")
            await send_webhook(session, webhook, payload_dict)


