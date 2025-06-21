from app.domain.webhooks.registry.registry_interface import WebhookRegistryInterface
from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_id
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.utils.crypto_utils import decrypt_secret
from app.constants.webhooks import WebhookEvent
from app.models.DB_tables.webhook import Webhook
from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import SecretStr, TypeAdapter, AnyHttpUrl


class SensorCreatedWebhookRegistry(WebhookRegistryInterface):
    _webhooks: List[WebhookConfig] = []

    @classmethod
    async def load(cls, session: AsyncSession) -> None:
        webhooks = await get_active_webhooks_by_event(session, WebhookEvent.SENSOR_CREATED.value)
        parsed: List[WebhookConfig] = []

        for row in webhooks:
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

        cls._webhooks = parsed

    @classmethod
    def get_all(cls) -> List[WebhookConfig]:
        return cls._webhooks

    @classmethod
    def add(cls, config: WebhookConfig) -> None:
        cls._webhooks.append(config)

    @classmethod
    def remove(cls, webhook_id: UUID) -> None:
        cls._webhooks = [w for w in cls._webhooks if w.id != webhook_id]

    @classmethod
    def replace(cls, config: WebhookConfig) -> None:
        cls.remove(config.id)
        cls.add(config)
