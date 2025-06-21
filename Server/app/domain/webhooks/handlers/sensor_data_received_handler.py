""""
from app.constants.webhooks import WebhookEvent
from app.models.schemas.rest.sensor_data_schemas import SensorDataOut
from app.domain.webhooks.webhook_logic import send_webhook
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.domain.webhooks.handlers.handler_interface import WebhookEventHandler
from sqlalchemy.ext.asyncio import AsyncSession

class SensorDataReceivedHandler(WebhookEventHandler[SensorDataOut]):
    payload_model = SensorDataOut  # For validation if raw dict passed

    async def handle(self, payload: SensorDataOut, session: AsyncSession) -> None:
        webhooks = await get_active_webhooks_by_event(
            session, event_type=WebhookEvent.SENSOR_DATA_RECEIVED.value
        )
        for webhook in webhooks:
            print(f"Dispatching 'sensor_data_received' to {webhook.target_url}")
            await send_webhook(session, webhook, payload.model_dump())


"""