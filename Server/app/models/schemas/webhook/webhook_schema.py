from datetime import datetime
from pydantic import BaseModel, AnyHttpUrl, Field
from uuid import UUID
from typing import Optional

class WebhookCreate(BaseModel):
    event_type: str
    target_url: AnyHttpUrl
    secret_label: Optional[str] = None
    custom_headers: Optional[dict[str, str]] = None


class WebhookRead(BaseModel):
    id: UUID
    event_type: str
    target_url: AnyHttpUrl
    enabled: bool
    retry_count: int
    last_error: Optional[str]
    last_triggered_at: Optional[datetime]

    model_config = {
        "from_attributes": True
    }
class WebhookDeletePayload(BaseModel):
    webhook_id: UUID


class WebhookUpdatePayload(BaseModel):
    webhook_id: UUID
    target_url: Optional[AnyHttpUrl] = None
    event_type: Optional[str] = None
    secret_label: Optional[str] = None
    custom_headers: Optional[dict[str, str]] = None
    enabled: Optional[bool] = None
