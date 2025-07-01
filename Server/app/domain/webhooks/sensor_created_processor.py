from typing import Any, List
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import SecretStr, TypeAdapter, AnyHttpUrl

from app.domain.webhooks.WebhookProcessorInterface import WebhookProcessorInterface
from app.models.schemas.webhook.webhook_schema import WebhookConfig, SensorCreatedPayload
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_id
from app.utils.crypto_utils import decrypt_secret
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.send_webhook import send_webhook
from app.models.DB_tables.webhook import Webhook


class SensorCreatedProcessor(WebhookProcessorInterface[SensorCreatedPayload]):
    """
    Webhook processor for SENSOR_CREATED events.

    Loads webhook configs, listens for new sensor creation,
    and dispatches configured HTTP POST requests to external targets.
    """

    _webhooks: List[WebhookConfig] = []
    payload_model = SensorCreatedPayload

    async def load(self, session: AsyncSession) -> None:
        """
        Load all webhook configs for the SENSOR_CREATED event from the database.

        Decrypts secrets and validates target URLs. Skips incomplete or broken configs.
        """
        db_webhooks: List[Webhook] = await get_active_webhooks_by_event(
            session, WebhookEvent.SENSOR_CREATED.value
        )

        parsed: List[WebhookConfig] = []
        for row in db_webhooks:
            if not row.secret_id:
                logger.warning("[SENSOR_CREATED] Webhook %s skipped: no secret_id", row.id)
                continue

            secret_obj = await get_user_secret_by_id(session, row.secret_id)
            if not secret_obj:
                logger.warning("[SENSOR_CREATED] Webhook %s skipped: secret not found", row.id)
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
        logger.info("[SENSOR_CREATED] Loaded %d webhooks", len(parsed))

    def get_all(self) -> List[WebhookConfig]:
        """
        Return all loaded webhook configurations for this processor.

        Returns:
            List[WebhookConfig]: Configs held in memory.
        """
        return self._webhooks

    def add(self, config: WebhookConfig) -> None:
        """
        Add a webhook config to memory (typically after creation).

        Args:
            config (WebhookConfig): Config to add.
        """
        self._webhooks.append(config)
        logger.info("[SENSOR_CREATED] Webhook added | id=%s", config.id)

    def remove(self, webhook_id: UUID) -> None:
        """
        Remove a webhook config from memory by its ID.

        Args:
            webhook_id (UUID): Webhook ID to remove.
        """
        self._webhooks = [w for w in self._webhooks if w.id != webhook_id]
        logger.info("[SENSOR_CREATED] Webhook removed | id=%s", webhook_id)

    def replace(self, config: WebhookConfig) -> None:
        """
        Replace an existing webhook configuration by ID.

        Args:
            config (WebhookConfig): Updated config with same ID.
        """
        self.remove(config.id)
        self.add(config)
        logger.info("[SENSOR_CREATED] Webhook replaced | id=%s", config.id)

    async def handle(self, payload: SensorCreatedPayload, session: AsyncSession) -> None:
        """
        Trigger this processor for a new sensor creation event.

        Dispatches the event payload to all registered webhooks.

        Args:
            payload (SensorCreatedPayload): The sensor creation data.
            session (AsyncSession): DB session for logging or persistence during delivery.
        """
        payload_dict: dict[str, Any] = payload.model_dump()
        for webhook in self._webhooks:
            try:
                logger.info(
                    "[SENSOR_CREATED] Dispatching webhook | sensor_id=%s | target=%s",
                    payload.sensor_id,
                    webhook.target_url
                )
                await send_webhook(session, webhook, payload_dict)
            except Exception as e:
                logger.exception(
                    "[SENSOR_CREATED] Failed to dispatch webhook | sensor_id=%s | target=%s",
                    payload.sensor_id,
                    webhook.target_url
                )
