# GRAPHQL OUTPUT TYPES
# These @strawberry.type classes define the GraphQL schema response models for:
# - Sensor metadata
# - Sensor data entries
# - Paginated query results

import strawberry
from datetime import datetime
from uuid import UUID


# ────────────────────────────────────────────────────────
# SENSOR METADATA TYPE
# ────────────────────────────────────────────────────────

@strawberry.type
class Sensor:
    """GraphQL type representing sensor metadata."""
    sensor_id: UUID = strawberry.field(name="sensor_id", description="Globally unique identifier for the sensor")
    name: str = strawberry.field(description="Human-readable name of the sensor")
    location: str | None = strawberry.field(description="Optional location or label (e.g. 'Lab 2')")
    model: str | None = strawberry.field(description="Sensor hardware model")
    is_active: bool = strawberry.field(name="is_active", description="True if the sensor is currently active")
    created_at: datetime = strawberry.field(name="created_at", description="Timestamp when the sensor was registered")
    updated_at: datetime = strawberry.field(name="updated_at", description="Timestamp of the last metadata update")


# ────────────────────────────────────────────────────────
# SENSOR DATA TYPE
# ────────────────────────────────────────────────────────

@strawberry.type
class SensorData:
    """GraphQL type representing a single sensor reading with full metrics."""
    id: UUID = strawberry.field(description="Database identifier for this reading")
    device_id: UUID = strawberry.field(name="device_id", description="Sensor UUID that generated the reading")
    timestamp: datetime = strawberry.field(description="Timestamp of when the data was recorded")

    temperature: float
    humidity: float

    pm1_0: float = strawberry.field(name="pm1_0")
    pm2_5: float = strawberry.field(name="pm2_5")
    pm10: float

    tvoc: float
    eco2: float
    aqi: float

    pmInAir1_0: int = strawberry.field(name="pmInAir1_0")
    pmInAir2_5: int = strawberry.field(name="pmInAir2_5")
    pmInAir10: int = strawberry.field(name="pmInAir10")

    particles0_3: int = strawberry.field(name="particles0_3")
    particles0_5: int = strawberry.field(name="particles0_5")
    particles1_0: int = strawberry.field(name="particles1_0")
    particles2_5: int = strawberry.field(name="particles2_5")
    particles5_0: int = strawberry.field(name="particles5_0")
    particles10: int = strawberry.field(name="particles10")

    compT: float = strawberry.field(name="compT")
    compRH: float = strawberry.field(name="compRH")

    rawT: float = strawberry.field(name="rawT")
    rawRH: float = strawberry.field(name="rawRH")

    rs0: int
    rs1: int
    rs2: int
    rs3: int

    co2: int


# ────────────────────────────────────────────────────────
# PAGINATED RESPONSE TYPES
# ────────────────────────────────────────────────────────

@strawberry.type
class PaginatedSensorData:
    """GraphQL type for paginated sensor data response."""
    items: list[SensorData] = strawberry.field(description="List of matching sensor data records")
    total: int = strawberry.field(description="Total number of matching records")
    page: int = strawberry.field(description="Current page number")
    page_size: int = strawberry.field(name="page_size", description="Number of results per page")


@strawberry.type
class PaginatedSensorMetadata:
    """GraphQL type for paginated sensor metadata response."""
    items: list[Sensor] = strawberry.field(description="List of matching sensor metadata entries")
    total: int = strawberry.field(description="Total number of matching entries")
    page: int = strawberry.field(description="Current page number")
    page_size: int = strawberry.field(name="page_size", description="Number of results per page")
