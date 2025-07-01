from typing import Dict
from uuid import UUID
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.constants.webhooks import WebhookEvent
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.domain.webhooks.WebhookProcessorInterface import WebhookProcessorInterface

# Import all concrete processors
from app.domain.webhooks.alert_processor import AlertWebhookProcessor
from app.domain.webhooks.sensor_status_changed_processor import SensorStatusChangedProcessor
from app.domain.webhooks.sensor_created_processor import SensorCreatedProcessor
from app.domain.webhooks.sensor_data_received_processor import SensorDataReceivedProcessor
from app.domain.webhooks.sensor_deleted_processor import SensorDeletedProcessor

from app.utils.exceptions_base import AppException
from app.infrastructure.database.transaction import run_in_transaction


class WebhookDispatcher:
    """
    Central registry and dispatcher for webhook events.

    Coordinates all registered WebhookProcessorInterface implementations.
    Allows:
    - Dynamic webhook config updates (add/remove/replace)
    - Lazy dispatch with runtime payload validation
    - Full registry refresh from DB
    """

    def __init__(self):
        # Dictionary of event type → processor
        self._processors: Dict[WebhookEvent, WebhookProcessorInterface] = {}

    def register(self, event: WebhookEvent, processor: WebhookProcessorInterface) -> None:
        """
        Register a processor instance for a specific event type.

        Args:
            event (WebhookEvent): Event this processor handles.
            processor (WebhookProcessorInterface): The processor implementation.
        """
        self._processors[event] = processor

    def can_handle(self, event: WebhookEvent) -> bool:
        """
        Check if a processor is available for a given event.
        """
        return event in self._processors

    async def refresh_registry(self, event: WebhookEvent, session: AsyncSession) -> None:
        """
        Refresh the webhook config for a single event from the DB.
        """
        processor = self._processors.get(event)
        if processor:
            await processor.load(session)

    def add_to_registry(self, config: WebhookConfig) -> None:
        """
        Add a webhook config to the appropriate processor.

        Args:
            config (WebhookConfig): Webhook config to register in memory.
        """
        event_type = config.event_type
        if event_type is None:
            return
        processor = self._processors.get(event_type)
        if processor:
            processor.add(config)

    def remove_from_registry(self, webhook_id: UUID, event_type: WebhookEvent) -> None:
        """
        Remove a webhook config from a specific processor by ID.
        """
        processor = self._processors.get(event_type)
        if processor:
            processor.remove(webhook_id)

    def replace_in_registry(self, config: WebhookConfig) -> None:
        """
        Replace an existing webhook config inside the registered processor.
        """
        event_type = config.event_type
        if event_type is None:
            return
        processor = self._processors.get(event_type)
        if processor:
            processor.replace(config)

    async def load_all_registries(self) -> None:
        """
        Refresh all webhook processors by reloading their configs from the DB.
        """
        async with run_in_transaction() as session:
            for processor in self._processors.values():
                await processor.load(session)

    async def dispatch(self, event: WebhookEvent, payload: BaseModel | dict) -> None:
        """
        Trigger a webhook event processor with a given payload.

        Performs:
        - Payload validation (if raw dict)
        - Type enforcement
        - Webhook delivery via the correct processor

        Args:
            event (WebhookEvent): Type of event to dispatch.
            payload (BaseModel | dict): The event payload.

        Raises:
            AppException: On unrecoverable internal error during dispatch.
        """
        processor = self._processors.get(event)
        if not processor:
            logger.warning("[WEBHOOK] No processor registered for event: %s", event)
            return

        # ─── Validate or Cast Payload ─────────────────────
        try:
            if isinstance(payload, dict):
                raw_model = getattr(processor, "payload_model", None)
                if not isinstance(raw_model, type) or not issubclass(raw_model, BaseModel):
                    logger.error("[WEBHOOK] Processor has no valid payload model for event: %s", event)
                    return
                payload = raw_model.model_validate(payload)
            elif not isinstance(payload, BaseModel):
                logger.error("[WEBHOOK] Invalid payload type for event: %s", event)
                return
        except ValidationError as e:
            logger.warning("[WEBHOOK] Payload validation failed for event %s: %s", event, str(e))
            return

        # ─── Dispatch the Event ────────────────────────────
        try:
            async with run_in_transaction() as session:
                await processor.handle(payload, session=session)
                logger.info("[WEBHOOK] Dispatched event successfully | event=%s", event)
        except AppException:
            raise
        except Exception as e:
            logger.exception("[WEBHOOK] Unhandled exception during dispatch | event=%s", event)
            raise AppException(
                message=f"Unhandled error in webhook dispatcher for event '{event}': {e}",
                status_code=500,
                public_message="Webhook dispatch failed.",
                domain="webhook"
            )


# ─── Singleton Dispatcher Instance ─────────────────────────────
dispatcher = WebhookDispatcher()

# ─── Processor Registrations ───────────────────────────────────

dispatcher.register(WebhookEvent.ALERT_TRIGGERED, AlertWebhookProcessor())
dispatcher.register(WebhookEvent.SENSOR_STATUS_CHANGED, SensorStatusChangedProcessor())
dispatcher.register(WebhookEvent.SENSOR_CREATED, SensorCreatedProcessor())
dispatcher.register(WebhookEvent.SENSOR_DATA_RECEIVED, SensorDataReceivedProcessor())
dispatcher.register(WebhookEvent.SENSOR_DELETED, SensorDeletedProcessor())
