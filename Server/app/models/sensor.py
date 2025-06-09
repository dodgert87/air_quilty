from sqlalchemy import String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from app.models.base import Base


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Match device_id in SensorData
    location: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    model: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
