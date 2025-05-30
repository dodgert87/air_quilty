from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from ..base import Base

class GraphQLLog(Base):
    __tablename__ = "graphql_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    user_id: Mapped[uuid.UUID | None]
    api_key: Mapped[str | None]
    ip_address: Mapped[str]
    query_name: Mapped[str | None]
    query_text: Mapped[str]
    variables: Mapped[dict] = mapped_column(JSON)
    response_status: Mapped[int]
    response_time_ms: Mapped[int]
    user_agent: Mapped[str]
    error_message: Mapped[str | None]
