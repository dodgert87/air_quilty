from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.webhooks.handlers.handler_interface import WebhookEventHandler
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn
from app.domain.webhooks.registry.alert_registry import AlertWebhookRegistry
from app.domain.webhooks.send_webhook import send_webhook

class AlertTriggeredHandler(WebhookEventHandler[SensorDataIn]):
    payload_model = SensorDataIn

    async def handle(self, payload: SensorDataIn, session: AsyncSession) -> None:
        data_dict: dict[str, Any] = payload.model_dump()

        for webhook in AlertWebhookRegistry.get_all():
            if not webhook.parameters:
                continue

            # Check if any parameter condition matches
            if self._matches_any_condition(data_dict, webhook.parameters):
                await send_webhook(session, webhook, data_dict)

    def _matches_any_condition(self, data: dict[str, Any], conditions: dict[str, list[float | None]]) -> bool:
        for param, (min_val, max_val) in conditions.items():

            if param not in data:
                continue

            value = data[param]

            if (min_val is None or value >= min_val) and (max_val is None or value <= max_val):
                return True

        return False
