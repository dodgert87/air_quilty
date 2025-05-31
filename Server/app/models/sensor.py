from datetime import datetime, timezone
from uuid import UUID
import uuid

from pydantic import BaseModel
from sqlalchemy import String, Float, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as SQLUUID

from app.models.base import Base


# ───────────────────────────────────────────────
# DOMAIN / API LAYER MODELS (Pydantic Schemas)
# ───────────────────────────────────────────────

class SensorDataIn(BaseModel):
    """
    Input schema for creating a new sensor record (used in POST requests).
    """
    device_id: str
    timestamp: datetime
    temperature: float
    humidity: float
    o2: float
    pm1_0: float
    pm2_5: float
    pm10: float
    tvoc: float
    eco2: float
    aqi: float

class SensorDataOut(SensorDataIn):
    """
    Output schema for returning sensor records (used in GET responses).
    """
    id: UUID


# ───────────────────────────────────────────────
# DATABASE MODEL (SQLAlchemy ORM)
# ───────────────────────────────────────────────

class SensorData(Base):
    """
    ORM mapping to the sensor_data table in PostgreSQL.
    """
    __tablename__ = "sensor_data"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    temperature: Mapped[float]
    humidity: Mapped[float]
    o2: Mapped[float]
    pm1_0: Mapped[float]
    pm2_5: Mapped[float]
    pm10: Mapped[float]
    tvoc: Mapped[float]
    eco2: Mapped[float]
    aqi: Mapped[float]
