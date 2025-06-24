from typing import Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from app.domain.webhooks.WebhookProcessorInterface import WebhookProcessorInterface
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn
from app.models.schemas.webhook.webhook_schema import WebhookConfig
from app.infrastructure.database.repository.webhook.webhook_repository import get_active_webhooks_by_event
from app.infrastructure.database.repository.restAPI.secret_repository import get_user_secret_by_id
from app.models.DB_tables.webhook import Webhook
from app.utils.crypto_utils import decrypt_secret
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.send_webhook import send_webhook


class AlertWebhookProcessor(WebhookProcessorInterface[SensorDataIn]):
    _webhooks: List[WebhookConfig] = []
    payload_model = SensorDataIn

    async def load(self, session: AsyncSession) -> None:
        db_webhooks: List[Webhook] = await get_active_webhooks_by_event(
            session, WebhookEvent.ALERT_TRIGGERED.value
        )

        parsed: List[WebhookConfig] = []
        for row in db_webhooks:
            if not row.parameters or not row.secret_id:
                continue

            secret_obj = await get_user_secret_by_id(session, row.secret_id)
            if not secret_obj:
                continue

            config = WebhookConfig(
                id=row.id,
                target_url=TypeAdapter(AnyHttpUrl).validate_python(row.target_url),
                secret=SecretStr(decrypt_secret(secret_obj.secret)),
                custom_headers=row.custom_headers,
                parameters=row.parameters,
                event_type=WebhookEvent.ALERT_TRIGGERED
            )
            parsed.append(config)

        self._webhooks = sorted(parsed, key=self._sort_key)

    def get_all(self) -> List[WebhookConfig]:
        return self._webhooks

    def add(self, config: WebhookConfig) -> None:
        self._webhooks.append(config)
        self._webhooks.sort(key=self._sort_key)

    def remove(self, webhook_id: UUID) -> None:
        self._webhooks = [w for w in self._webhooks if w.id != webhook_id]

    def replace(self, config: WebhookConfig) -> None:
        self.remove(config.id)
        self.add(config)

    async def handle(self, payload: SensorDataIn, session: AsyncSession) -> None:
        data_dict: dict[str, Any] = payload.model_dump()

        for webhook in self._webhooks:
            if not webhook.parameters:
                continue
            if self._matches_any_condition(data_dict, webhook.parameters):
                await send_webhook(session, webhook, data_dict)

    def _matches_any_condition(self, data: dict[str, Any], conditions: dict[str, list[float | None]]) -> bool:
        for param, (min_val, max_val) in conditions.items():
            if param not in data:
                continue
            value = data[param]
            if (min_val is None or value >= min_val) and (max_val is None or value <= max_val):
                return True
        return False

    def _sort_key(self, w: WebhookConfig):
        params = w.parameters or {}
        return tuple(
            sorted((p, params.get(p, [float("-inf")])[0] or float("-inf")) for p in params)
        )
