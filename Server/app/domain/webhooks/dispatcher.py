from typing import Dict, Type
from uuid import UUID
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.webhooks.registry.alert_registry import AlertWebhookRegistry
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.domain.webhooks.handlers.alert_triggered_handler import AlertTriggeredHandler
#from app.domain.webhooks.handlers.sensor_status_changed import SensorStatusChangedHandler
#from app.domain.webhooks.handlers.sensor_created_handler import SensorCreatedHandler
#from app.domain.webhooks.handlers.sensor_data_received_handler import SensorDataReceivedHandler
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.handlers.handler_interface import WebhookEventHandler

from app.utils.exceptions_base import AppException
from app.infrastructure.database.transaction import run_in_transaction


class WebhookDispatcher:
    def __init__(self):
        self._handlers: Dict[WebhookEvent, WebhookEventHandler] = {}
        self._registry_classes: Dict[WebhookEvent, type] = {}

    def register_with_registry(self, event: WebhookEvent, handler: WebhookEventHandler, registry_class: type):
        self._handlers[event] = handler
        self._registry_classes[event] = registry_class

    def can_handle(self, event: WebhookEvent) -> bool:
        return event in self._handlers

    async def dispatch(self, event: WebhookEvent, payload: BaseModel | dict) -> None:
        #print(f"Dispatching event '{event}' with payload: {payload}")
        handler = self._handlers.get(event)
        if not handler:
            return

        try:
            if isinstance(payload, dict):
                raw_model = getattr(handler, "payload_model", None)
                if not isinstance(raw_model, type) or not issubclass(raw_model, BaseModel):
                    return
                payload = raw_model.model_validate(payload)
            elif not isinstance(payload, BaseModel):
                return
        except ValidationError:
            return

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

    async def refresh_registry(self, event: WebhookEvent, session: AsyncSession) -> None:
        registry_class = self._registry_classes.get(event)
        if registry_class:
            await registry_class.load(session)

    def add_to_registry(self, config: WebhookConfig) -> None:
        registry_class = self._registry_classes.get(config.event_type) # type: ignore
        if registry_class:
            registry_class.add(config)

    def remove_from_registry(self, webhook_id: UUID, event_type: WebhookEvent) -> None:
        registry_class = self._registry_classes.get(event_type)
        if registry_class:
            registry_class.remove(webhook_id)

    def replace_in_registry(self, config: WebhookConfig) -> None:
        registry_class = self._registry_classes.get(config.event_type) # type: ignore
        if registry_class:
            registry_class.replace(config)

    async def load_all_registries(self) -> None:
        async with run_in_transaction() as session:
            for event, registry_class in self._registry_classes.items():
                await registry_class.load(session)


# ─── Singleton Dispatcher Instance ─────────────────────────────
dispatcher = WebhookDispatcher()

# ─── Handler Registrations ─────────────────────────────────────
#dispatcher.register(WebhookEvent.SENSOR_CREATED, SensorCreatedHandler())
#dispatcher.register(WebhookEvent.SENSOR_DATA_RECEIVED, SensorDataReceivedHandler())
#dispatcher.register(WebhookEvent.SENSOR_STATUS_CHANGED, SensorStatusChangedHandler())
dispatcher.register_with_registry(
    WebhookEvent.ALERT_TRIGGERED,
    AlertTriggeredHandler(),
    AlertWebhookRegistry
)
