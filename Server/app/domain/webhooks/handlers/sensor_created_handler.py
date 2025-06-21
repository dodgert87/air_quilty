from app.domain.webhooks.webhook_logic import send_webhook
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.models.schemas.webhook.sensor_created import SensorCreatedPayload
from app.domain.webhooks.handlers.base import WebhookEventHandler
from sqlalchemy.ext.asyncio import AsyncSession

class SensorCreatedHandler(WebhookEventHandler[SensorCreatedPayload]):
    async def handle(self, payload: SensorCreatedPayload, session: AsyncSession) -> None:
        webhooks = await get_active_webhooks_by_event(session, event_type="sensor_created")
        for webhook in webhooks:
            print(f"Sending sensor_created webhook to {webhook.target_url} for sensor {payload.sensor_id}")
            await send_webhook(session, webhook, payload.model_dump())