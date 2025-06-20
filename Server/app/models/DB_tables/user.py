from typing import Optional
from sqlalchemy import TIMESTAMP, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid
import enum

from app.models.DB_tables.base import Base

class RoleEnum(str, enum.Enum):
    admin = "admin"
    developer = "developer"
    authenticated = "authenticated"
    guest = "guest"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[RoleEnum]
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    last_login: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), default=None)
