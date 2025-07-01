from typing import Any, List
from uuid import UUID
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import SecretStr, TypeAdapter, AnyHttpUrl

from app.domain.webhooks.WebhookProcessorInterface import WebhookProcessorInterface
from app.models.schemas.rest.sensor_schemas import SensorOut
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_id
from app.utils.crypto_utils import decrypt_secret
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.send_webhook import send_webhook
from app.models.DB_tables.webhook import Webhook


class SensorStatusChangedProcessor(WebhookProcessorInterface[SensorOut]):
    """
    Webhook processor for SENSOR_STATUS_CHANGED events.

    Notifies all subscribed webhook endpoints when a sensor's activation
    status or operational condition changes.
    """

    _webhooks: List[WebhookConfig] = []
    payload_model = SensorOut

    async def load(self, session: AsyncSession) -> None:
        """
        Load active webhook configurations for SENSOR_STATUS_CHANGED.

        Retrieves configs from DB, decrypts secrets, and validates target URLs.
        """
        db_webhooks = await get_active_webhooks_by_event(
            session, WebhookEvent.SENSOR_STATUS_CHANGED.value
        )
        parsed: List[WebhookConfig] = []

        for row in db_webhooks:
            if not row.secret_id:
                logger.warning("[SENSOR_STATUS_CHANGED] Skipping webhook | id=%s | reason=no secret_id", row.id)
                continue

            secret_obj = await get_user_secret_by_id(session, row.secret_id)
            if not secret_obj:
                logger.warning("[SENSOR_STATUS_CHANGED] Skipping webhook | id=%s | reason=secret not found", row.id)
                continue

            parsed.append(WebhookConfig(
                id=row.id,
                event_type=WebhookEvent(row.event_type),
                target_url=TypeAdapter(AnyHttpUrl).validate_python(row.target_url),
                secret=SecretStr(decrypt_secret(secret_obj.secret)),
                custom_headers=row.custom_headers,
                parameters=row.parameters
            ))

        self._webhooks = parsed
        logger.info("[SENSOR_STATUS_CHANGED] Loaded %d webhooks", len(parsed))

    def get_all(self) -> List[WebhookConfig]:
        """
        Return all currently loaded webhook configurations.
        """
        return self._webhooks

    def add(self, config: WebhookConfig) -> None:
        """
        Add a new webhook configuration to memory.
        """
        self._webhooks.append(config)
        logger.info("[SENSOR_STATUS_CHANGED] Webhook added | id=%s", config.id)

    def remove(self, webhook_id: UUID) -> None:
        """
        Remove a webhook configuration from memory by its ID.
        """
        self._webhooks = [w for w in self._webhooks if w.id != webhook_id]
        logger.info("[SENSOR_STATUS_CHANGED] Webhook removed | id=%s", webhook_id)

    def replace(self, config: WebhookConfig) -> None:
        """
        Replace an existing webhook configuration by ID.
        """
        self.remove(config.id)
        self.add(config)
        logger.info("[SENSOR_STATUS_CHANGED] Webhook replaced | id=%s", config.id)

    async def handle(self, payload: SensorOut, session: AsyncSession) -> None:
        """
        Trigger webhook notifications in response to sensor status changes.

        Args:
            payload (SensorOut): The updated sensor metadata.
            session (AsyncSession): Active DB session for webhook logging.
        """
        payload_dict: dict[str, Any] = payload.model_dump()

        for webhook in self._webhooks:
            try:
                logger.info(
                    "[SENSOR_STATUS_CHANGED] Dispatching webhook | sensor_id=%s | target=%s",
                    payload.sensor_id, webhook.target_url
                )
                await send_webhook(session, webhook, payload_dict)
            except Exception as e:
                logger.exception(
                    "[SENSOR_STATUS_CHANGED] Failed to send webhook | sensor_id=%s | target=%s",
                    payload.sensor_id, webhook.target_url
                )
