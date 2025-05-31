import enum
import uuid
from sqlalchemy import String, Integer, Enum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.models.base import Base

class HTTPMethod(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class RestLog(Base):
    __tablename__ = "rest_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))
    user_id: Mapped[uuid.UUID | None]
    api_key: Mapped[str | None]
    ip_address: Mapped[str]
    method: Mapped[HTTPMethod]
    endpoint: Mapped[str]
    query_params: Mapped[dict] = mapped_column(JSON)
    request_body: Mapped[dict] = mapped_column(JSON)
    response_status: Mapped[int]
    response_time_ms: Mapped[int]
    user_agent: Mapped[str]
    error_message: Mapped[str | None]
