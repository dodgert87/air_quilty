from sqlalchemy import String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid
from ..base import Base

class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))
    webhook_id: Mapped[uuid.UUID]  # assumed to point to some webhook table in future
    target_url: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSON)
    response_status: Mapped[int]
    response_time_ms: Mapped[int]
    delivery_attempt: Mapped[int]
    error_message: Mapped[str | None]
