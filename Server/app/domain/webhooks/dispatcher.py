from typing import Dict
from uuid import UUID
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.webhooks import WebhookEvent
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.domain.webhooks.WebhookProcessorInterface import WebhookProcessorInterface
# Updated imports: use unified processors
from app.domain.webhooks.alert_processor import AlertWebhookProcessor
from app.domain.webhooks.sensor_status_changed_processor import SensorStatusChangedProcessor
from app.domain.webhooks.sensor_created_processor import SensorCreatedProcessor
from app.domain.webhooks.sensor_data_received_processor import SensorDataReceivedProcessor
from app.domain.webhooks.sensor_deleted_processor import SensorDeletedProcessor

from app.utils.exceptions_base import AppException
from app.infrastructure.database.transaction import run_in_transaction


class WebhookDispatcher:
    def __init__(self):
        self._processors: Dict[WebhookEvent, WebhookProcessorInterface] = {}

    def register(self, event: WebhookEvent, processor: WebhookProcessorInterface) -> None:
        self._processors[event] = processor

    def can_handle(self, event: WebhookEvent) -> bool:
        return event in self._processors

    async def dispatch(self, event: WebhookEvent, payload: BaseModel | dict) -> None:
        processor = self._processors.get(event)
        if not processor:
            return

        try:
            if isinstance(payload, dict):
                raw_model = getattr(processor, "payload_model", None)
                if not isinstance(raw_model, type) or not issubclass(raw_model, BaseModel):
                    return
                payload = raw_model.model_validate(payload)
            elif not isinstance(payload, BaseModel):
                return
        except ValidationError:
            return

        try:
            async with run_in_transaction() as session:
                await processor.handle(payload, session=session)
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
        processor = self._processors.get(event)
        if processor:
            await processor.load(session)

    def add_to_registry(self, config: WebhookConfig) -> None:

        event_type = config.event_type
        if event_type is None:
            return
        processor = self._processors.get(event_type)
        if processor:
            processor.add(config)

    def remove_from_registry(self, webhook_id: UUID, event_type: WebhookEvent) -> None:
        processor = self._processors.get(event_type)
        if processor:
            processor.remove(webhook_id)

    def replace_in_registry(self, config: WebhookConfig) -> None:
        event_type = config.event_type
        if event_type is None:
            return
        processor = self._processors.get(event_type)
        if processor:
            processor.replace(config)

    async def load_all_registries(self) -> None:
        async with run_in_transaction() as session:
            for processor in self._processors.values():
                await processor.load(session)


# ─── Singleton Dispatcher Instance ─────────────────────────────
dispatcher = WebhookDispatcher()

# ─── Processor Registrations ───────────────────────────────────

dispatcher.register(WebhookEvent.ALERT_TRIGGERED, AlertWebhookProcessor())
dispatcher.register(WebhookEvent.SENSOR_STATUS_CHANGED, SensorStatusChangedProcessor())
dispatcher.register(WebhookEvent.SENSOR_CREATED, SensorCreatedProcessor())
dispatcher.register(WebhookEvent.SENSOR_DATA_RECEIVED, SensorDataReceivedProcessor())
dispatcher.register(WebhookEvent.SENSOR_DELETED, SensorDeletedProcessor())
