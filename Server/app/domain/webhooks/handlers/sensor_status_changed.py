"""
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.webhook_logic import send_webhook
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.models.schemas.rest.sensor_schemas import SensorOut
from app.domain.webhooks.handlers.handler_interface import WebhookEventHandler
from sqlalchemy.ext.asyncio import AsyncSession


class SensorStatusChangedHandler(WebhookEventHandler[SensorOut]):
    payload_model = SensorOut

    async def handle(self, payload: SensorOut, session: AsyncSession) -> None:
        webhooks = await get_active_webhooks_by_event(
            session, event_type=WebhookEvent.SENSOR_STATUS_CHANGED.value
        )
        for webhook in webhooks:
            print(f"Dispatching 'sensor_status_changed' to {webhook.target_url}")
            await send_webhook(session, webhook, payload.model_dump())
"""