from typing import Any, List
from uuid import UUID
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import SecretStr, TypeAdapter, AnyHttpUrl

from app.domain.webhooks.WebhookProcessorInterface import WebhookProcessorInterface
from app.models.schemas.rest.sensor_data_schemas import SensorDataOut
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_id
from app.utils.crypto_utils import decrypt_secret
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.send_webhook import send_webhook


class SensorDataReceivedProcessor(WebhookProcessorInterface[SensorDataOut]):
    """
    Webhook processor for SENSOR_DATA_RECEIVED events.

    Dispatches raw sensor data outputs to all registered external endpoints.
    This processor does not apply any filtering — it sends all received data.
    """

    _webhooks: List[WebhookConfig] = []
    payload_model = SensorDataOut

    async def load(self, session: AsyncSession) -> None:
        """
        Load all SENSOR_DATA_RECEIVED webhook configs from the database.

        Decrypts user secrets and parses configs into memory.
        Logs warnings for incomplete rows.
        """
        db_webhooks = await get_active_webhooks_by_event(
            session, WebhookEvent.SENSOR_DATA_RECEIVED.value
        )

        parsed: List[WebhookConfig] = []
        for row in db_webhooks:
            if not row.secret_id:
                logger.warning("[SENSOR_DATA_RECEIVED] Webhook %s skipped: no secret_id", row.id)
                continue

            secret_obj = await get_user_secret_by_id(session, row.secret_id)
            if not secret_obj:
                logger.warning("[SENSOR_DATA_RECEIVED] Webhook %s skipped: secret not found", row.id)
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
        logger.info("[SENSOR_DATA_RECEIVED] Loaded %d webhooks", len(parsed))

    def get_all(self) -> List[WebhookConfig]:
        """
        Return all in-memory webhook configurations.
        """
        return self._webhooks

    def add(self, config: WebhookConfig) -> None:
        """
        Add a new webhook configuration to memory.
        """
        self._webhooks.append(config)
        logger.info("[SENSOR_DATA_RECEIVED] Webhook added | id=%s", config.id)

    def remove(self, webhook_id: UUID) -> None:
        """
        Remove a webhook config by ID.
        """
        self._webhooks = [w for w in self._webhooks if w.id != webhook_id]
        logger.info("[SENSOR_DATA_RECEIVED] Webhook removed | id=%s", webhook_id)

    def replace(self, config: WebhookConfig) -> None:
        """
        Replace an existing config (by ID) with a new one.
        """
        self.remove(config.id)
        self.add(config)
        logger.info("[SENSOR_DATA_RECEIVED] Webhook replaced | id=%s", config.id)

    async def handle(self, payload: SensorDataOut, session: AsyncSession) -> None:
        """
        Trigger all registered webhooks with the full sensor data output.

        This processor assumes that every received sensor payload should be sent.

        Args:
            payload (SensorDataOut): The sensor data output model.
            session (AsyncSession): DB session for tracking delivery/logging.
        """
        payload_dict: dict[str, Any] = payload.model_dump()

        for webhook in self._webhooks:
            try:
                logger.info(
                    "[SENSOR_DATA_RECEIVED] Dispatching webhook | sensor_id=%s | target=%s",
                    payload.id, webhook.target_url
                )
                await send_webhook(session, webhook, payload_dict)
            except Exception as e:
                logger.exception(
                    "[SENSOR_DATA_RECEIVED] Failed to send webhook | sensor_id=%s | target=%s",
                    payload.id, webhook.target_url
                )
