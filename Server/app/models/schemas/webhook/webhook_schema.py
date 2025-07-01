# WEBHOOK CONFIGURATION & EVENT MODELS
# These models define:
# - The configuration and lifecycle of webhook subscriptions
# - The payloads emitted when specific webhook events occur (sensor created, deleted, etc.)

from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, AnyHttpUrl, ConfigDict, Field, SecretStr, TypeAdapter

from app.models.DB_tables.webhook import Webhook
from app.constants.webhooks import WebhookEvent


# ────────────────────────────────────────────────────────
# EVENT PAYLOADS (Sent to External Systems)
# ────────────────────────────────────────────────────────

class SensorCreatedPayload(BaseModel):
    """Payload structure for the 'sensor.created' webhook event."""
    sensor_id: UUID = Field(..., description="UUID of the newly registered sensor")
    name: str = Field(..., description="Sensor display name")
    created_at: datetime = Field(..., description="Time of registration")
    location: str | None = Field(None, description="Optional location of the sensor")
    model: str | None = Field(None, description="Optional model of the sensor hardware")


class SensorDeletedPayload(BaseModel):
    """Payload structure for the 'sensor.deleted' webhook event."""
    sensor_id: UUID = Field(..., description="UUID of the deleted sensor")
    deleted_at: datetime = Field(..., description="Timestamp when the sensor was deleted")


# ────────────────────────────────────────────────────────
# WEBHOOK CONFIGURATION MODELS
# ────────────────────────────────────────────────────────

class WebhookConfig(BaseModel):
    """Internal model for loading full webhook config (including resolved secret)."""
    id: UUID = Field(..., description="Webhook ID")
    target_url: AnyHttpUrl = Field(..., description="Destination URL for webhook delivery")
    event_type: Optional[WebhookEvent] = Field(None, description="Event type this webhook listens for")
    secret: SecretStr = Field(..., description="Signing secret used for webhook payload integrity")
    custom_headers: Optional[dict] = Field(None, description="Optional custom HTTP headers")
    parameters: Optional[dict[str, list[float | None]]] = Field(
        None,
        description="Optional parameter filters as {field_name: [min, max]}"
    )

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


# ────────────────────────────────────────────────────────
# API REQUEST/RESPONSE MODELS
# ────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    """Request payload for creating a new webhook subscription."""
    event_type: str = Field(..., description="Event name (e.g., 'sensor.created')")
    target_url: AnyHttpUrl = Field(..., description="URL to which the event will be POSTed")
    secret_label: Optional[str] = Field(None, description="Label of the secret used to sign the webhook")
    custom_headers: Optional[dict[str, str]] = Field(None, description="Optional HTTP headers to include")
    parameters: Optional[dict[str, tuple[Optional[float], Optional[float]]]] = Field(
        None,
        description="Optional filters as {field: (min, max)}. Null = unbounded."
    )


class WebhookRead(BaseModel):
    """Response model for listing or retrieving a webhook configuration."""
    id: UUID = Field(..., description="Webhook ID")
    event_type: str = Field(..., description="Event this webhook listens for")
    target_url: AnyHttpUrl = Field(..., description="Webhook destination URL")
    enabled: bool = Field(..., description="True if the webhook is active")
    last_error: Optional[str] = Field(None, description="Last error encountered during delivery (if any)")
    last_triggered_at: Optional[datetime] = Field(None, description="Last successful or attempted trigger")
    parameters: Optional[dict[str, tuple[Optional[float], Optional[float]]]] = Field(
        None,
        description="Optional field filters as {field: (min, max)}"
    )

    model_config = ConfigDict(from_attributes=True)


class WebhookDeletePayload(BaseModel):
    """Request payload for deleting a webhook."""
    webhook_id: UUID = Field(..., description="ID of the webhook to delete")


class WebhookUpdatePayload(BaseModel):
    """Request payload to update an existing webhook's configuration."""
    webhook_id: UUID = Field(..., description="ID of the webhook to update")
    target_url: Optional[AnyHttpUrl] = Field(None, description="New URL for webhook delivery")
    event_type: Optional[str] = Field(None, description="New event type to listen for")
    secret_label: Optional[str] = Field(None, description="New signing secret label")
    custom_headers: Optional[dict[str, str]] = Field(None, description="New or updated HTTP headers")
    parameters: Optional[dict[str, tuple[Optional[float], Optional[float]]]] = Field(
        None,
        description="New field filters as {field: (min, max)}"
    )
    enabled: Optional[bool] = Field(None, description="Enable or disable this webhook")
