import enum
from sqlalchemy import Enum, ForeignKey, Integer, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from app.models.base import Base

class ProtocolEnum(str, enum.Enum):
    rest = "rest"
    graphql = "graphql"
    webhook = "webhook"
    websocket = "websocket"

class RateLimit(Base):
    __tablename__ = "rate_limits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None]
    api_key: Mapped[str | None] = mapped_column(ForeignKey("api_keys.key"), nullable=True)
    protocol: Mapped[ProtocolEnum]
    limit: Mapped[int]
    window_start: Mapped[datetime]
    request_count: Mapped[int]
    max_duration_sec: Mapped[int | None]
    used_duration_sec: Mapped[int | None]
    interval_hours: Mapped[int | None]
    last_used: Mapped[datetime]
