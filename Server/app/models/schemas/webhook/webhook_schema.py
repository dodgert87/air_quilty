from datetime import datetime
from pydantic import BaseModel, AnyHttpUrl, ConfigDict, Field, SecretStr, TypeAdapter
from uuid import UUID
from typing import Optional

from app.models.DB_tables.webhook import Webhook
from app.constants.webhooks import WebhookEvent

class WebhookConfig(BaseModel):
    id: UUID
    target_url: AnyHttpUrl
    event_type: Optional[WebhookEvent] = None
    secret: SecretStr
    custom_headers: Optional[dict] = None
    parameters: Optional[dict[str, list[float | None]]] = None

    @classmethod
    def from_orm_and_secret(cls, webhook: Webhook, raw_secret: str) -> "WebhookConfig":
        return cls(
            id=webhook.id,
            event_type=WebhookEvent(webhook.event_type),
            target_url=TypeAdapter(AnyHttpUrl).validate_python(webhook.target_url),
            secret=SecretStr(raw_secret),
            custom_headers=webhook.custom_headers,
            parameters=webhook.parameters
        )

class WebhookCreate(BaseModel):
    event_type: str
    target_url: AnyHttpUrl
    secret_label: Optional[str] = None
    custom_headers: Optional[dict[str, str]] = None
    parameters: Optional[dict[str, tuple[Optional[float], Optional[float]]]] = None



class WebhookRead(BaseModel):
    id: UUID
    event_type: str
    target_url: AnyHttpUrl
    enabled: bool
    last_error: Optional[str]
    last_triggered_at: Optional[datetime]
    parameters: Optional[dict[str, tuple[Optional[float], Optional[float]]]] = None

    model_config = ConfigDict(from_attributes=True)


class WebhookDeletePayload(BaseModel):
    webhook_id: UUID


class WebhookUpdatePayload(BaseModel):
    webhook_id: UUID
    target_url: Optional[AnyHttpUrl] = None
    event_type: Optional[str] = None
    secret_label: Optional[str] = None
    custom_headers: Optional[dict[str, str]] = None
    parameters: Optional[dict[str, tuple[Optional[float], Optional[float]]]] = None
    enabled: Optional[bool] = None


class SensorDeletedPayload(BaseModel):
    sensor_id: UUID
    deleted_at: datetime
