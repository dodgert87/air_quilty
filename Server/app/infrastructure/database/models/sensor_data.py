from sqlalchemy import String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from ..base import Base

class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)

    temperature: Mapped[float]
    humidity: Mapped[float]
    o2: Mapped[float]
    pm1_0: Mapped[float]
    pm2_5: Mapped[float]
    pm10: Mapped[float]
    tvoc: Mapped[float]
    eco2: Mapped[float]
    aqi: Mapped[float]
