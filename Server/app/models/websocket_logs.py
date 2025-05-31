from sqlalchemy import String, Integer, Enum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid
import enum
from app.models.base import Base

class WebSocketEvent(str, enum.Enum):
    connect = "connect"
    disconnect = "disconnect"
    message = "message"
    error = "error"

class Direction(str, enum.Enum):
    client_to_server = "client_to_server"
    server_to_client = "server_to_client"

class WebSocketLog(Base):
    __tablename__ = "websocket_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))
    connection_id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID | None]
    ip_address: Mapped[str]
    event_type: Mapped[WebSocketEvent]
    direction: Mapped[Direction]
    payload: Mapped[dict] = mapped_column(JSON)
    status_code: Mapped[int | None]
    error_message: Mapped[str | None]
