import strawberry
from datetime import datetime
from uuid import UUID


@strawberry.type
class Sensor:
    sensor_id: UUID = strawberry.field(name="sensor_id")
    name: str
    location: str | None
    model: str | None
    is_active: bool = strawberry.field(name="is_active")
    created_at: datetime = strawberry.field(name="created_at")
    updated_at: datetime = strawberry.field(name="updated_at")


@strawberry.type
class SensorData:
    id: UUID
    device_id: UUID = strawberry.field(name="device_id")
    timestamp: datetime

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


@strawberry.type
class PaginatedSensorData:
    items: list[SensorData]
    total: int
    page: int
    page_size: int = strawberry.field(name="page_size")

@strawberry.type
class PaginatedSensorMetadata:
    items: list[Sensor]
    total: int
    page: int
    page_size: int = strawberry.field(name="page_size")
