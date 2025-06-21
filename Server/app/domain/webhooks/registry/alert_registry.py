from typing import List, Optional
from uuid import UUID
from pydantic import AnyHttpUrl, SecretStr, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_id
from app.utils.crypto_utils import decrypt_secret
from app.domain.webhooks.registry.registry_interface import WebhookRegistryInterface
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.constants.webhooks import WebhookEvent
from app.models.DB_tables.webhook import Webhook


class AlertWebhookRegistry(WebhookRegistryInterface):
    _webhooks: List[WebhookConfig] = []
    print("AlertWebhookRegistry initialized with empty webhook list.")

    @classmethod
    async def load(cls, session: AsyncSession) -> None:
        print("Loading alert webhooks from database...")
        db_webhooks: List[Webhook] = await get_active_webhooks_by_event(session, WebhookEvent.ALERT_TRIGGERED.value)

        parsed: List[WebhookConfig] = []
        for row in db_webhooks:
            if not row.parameters:
                continue  # Alert webhooks must have parameters
            if not row.secret_id:
                continue  # no secret to use

            secret_obj = await get_user_secret_by_id(session, row.secret_id)
            if not secret_obj:
                continue  # revoked or missing
            config = WebhookConfig(
                id=row.id,
                target_url = TypeAdapter(AnyHttpUrl).validate_python(row.target_url),
                secret=SecretStr(decrypt_secret(secret_obj.secret)),
                custom_headers=row.custom_headers,
                parameters=row.parameters
            )
            parsed.append(config)
            print(f"Parsed webhook: {config.id} with parameters {config.parameters}")

        # Flatten and sort by (param name, min)
        def sort_key(w: WebhookConfig):
            params = w.parameters or {}
            return tuple(
                sorted(
                    (p, params.get(p, [float("-inf")])[0] or float("-inf"))
                    for p in params
                )
            )

        cls._webhooks = sorted(parsed, key=sort_key)


    @classmethod
    def get_all(cls) -> List[WebhookConfig]:
        return cls._webhooks

    @classmethod
    def add(cls, config: WebhookConfig) -> None:
        cls._webhooks.append(config)
        def sort_key(w: WebhookConfig):
            params = w.parameters or {}
            return tuple(
                sorted(
                    (p, params.get(p, [float("-inf")])[0] or float("-inf"))
                    for p in params
                )
            )

        cls._webhooks.sort(key=sort_key)

    @classmethod
    def remove(cls, webhook_id: UUID) -> None:
        cls._webhooks = [w for w in cls._webhooks if w.id != webhook_id]

    @classmethod
    def replace(cls, config: WebhookConfig) -> None:
        cls.remove(config.id)
        cls.add(config)
