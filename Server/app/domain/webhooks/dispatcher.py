from typing import Dict, Type
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.webhooks.handlers.sensor_status_changed import SensorStatusChangedHandler
from app.domain.webhooks.handlers.sensor_created_handler import SensorCreatedHandler
from app.domain.webhooks.handlers.sensor_data_received_handler import SensorDataReceivedHandler
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.handlers.base import WebhookEventHandler

from app.utils.exceptions_base import AppException
from app.infrastructure.database.transaction import run_in_transaction


class WebhookDispatcher:
    def __init__(self):
        self._handlers: Dict[WebhookEvent, WebhookEventHandler] = {}

    def register(self, event: WebhookEvent, handler: WebhookEventHandler):
        self._handlers[event] = handler

    def can_handle(self, event: WebhookEvent) -> bool:
        return event in self._handlers

    async def dispatch(self, event: WebhookEvent, payload: BaseModel | dict) -> None:
        handler = self._handlers.get(event)
        if not handler:
            return  # No handler, skip silently

        try:
            if isinstance(payload, dict):
                raw_model = getattr(handler, "payload_model", None)
                if not isinstance(raw_model, type) or not issubclass(raw_model, BaseModel):
                    return
                payload_model: Type[BaseModel] = raw_model
                payload = payload_model.model_validate(payload)

            elif not isinstance(payload, BaseModel):
                return

        except ValidationError:
            return  # Invalid payload, skip

        try:
            async with run_in_transaction() as session:
                await handler.handle(payload, session=session)
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                message=f"Unhandled error in webhook dispatcher for event '{event}': {e}",
                status_code=500,
                public_message="Webhook dispatch failed.",
                domain="webhook"
            )


# ─── Singleton Dispatcher Instance ─────────────────────────────
dispatcher = WebhookDispatcher()

# ─── Handler Registrations ─────────────────────────────────────
dispatcher.register(WebhookEvent.SENSOR_CREATED, SensorCreatedHandler())
dispatcher.register(WebhookEvent.SENSOR_DATA_RECEIVED, SensorDataReceivedHandler())
dispatcher.register(WebhookEvent.SENSOR_STATUS_CHANGED, SensorStatusChangedHandler())

