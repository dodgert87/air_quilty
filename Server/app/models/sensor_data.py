from sqlalchemy import String, Float, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
import uuid
from app.models.base import Base



class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), index=True)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Core metrics
    temperature: Mapped[float]
    humidity: Mapped[float]
    pm1_0: Mapped[float]
    pm2_5: Mapped[float]
    pm10: Mapped[float]
    tvoc: Mapped[float]
    eco2: Mapped[float]
    aqi: Mapped[float]

    # Extended metrics
    pmInAir1_0: Mapped[int]
    pmInAir2_5: Mapped[int]
    pmInAir10: Mapped[int]
    particles0_3: Mapped[int]
    particles0_5: Mapped[int]
    particles1_0: Mapped[int]
    particles2_5: Mapped[int]
    particles5_0: Mapped[int]
    particles10: Mapped[int]
    compT: Mapped[float]
    compRH: Mapped[float]
    rawT: Mapped[float]
    rawRH: Mapped[float]
    rs0: Mapped[int]
    rs1: Mapped[int]
    rs2: Mapped[int]
    rs3: Mapped[int]
    co2: Mapped[int]
