from typing import Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import SecretStr, TypeAdapter, AnyHttpUrl


from app.domain.webhooks.WebhookProcessorInterface import WebhookProcessorInterface
from app.models.schemas.webhook.webhook_schema import SensorDeletedPayload, WebhookConfig
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_id
from app.utils.crypto_utils import decrypt_secret
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.send_webhook import send_webhook
from app.models.DB_tables.webhook import Webhook


class SensorDeletedProcessor(WebhookProcessorInterface[SensorDeletedPayload]):
    _webhooks: List[WebhookConfig] = []
    payload_model = SensorDeletedPayload

    async def load(self, session: AsyncSession) -> None:
        db_webhooks = await get_active_webhooks_by_event(session, WebhookEvent.SENSOR_DELETED.value)
        parsed: List[WebhookConfig] = []

        for row in db_webhooks:
            if not row.secret_id:
                continue

            secret_obj = await get_user_secret_by_id(session, row.secret_id)
            if not secret_obj:
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

    def get_all(self) -> List[WebhookConfig]:
        return self._webhooks

    def add(self, config: WebhookConfig) -> None:
        self._webhooks.append(config)

    def remove(self, webhook_id: UUID) -> None:
        self._webhooks = [w for w in self._webhooks if w.id != webhook_id]

    def replace(self, config: WebhookConfig) -> None:
        self.remove(config.id)
        self.add(config)

    async def handle(self, payload: SensorDeletedPayload, session: AsyncSession) -> None:
        payload_dict: dict[str, Any] = payload.model_dump()

        for webhook in self._webhooks:
            print(f"Dispatching 'sensor_deleted' webhook to {webhook.target_url}")
            await send_webhook(session, webhook, payload_dict)
