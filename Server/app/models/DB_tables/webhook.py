from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid
from app.models.DB_tables.base import Base

class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g., "sensor_created", or "*"
    target_url: Mapped[str] = mapped_column(String, nullable=False)

    secret_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user_secrets.id"), nullable=True)
    custom_headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
