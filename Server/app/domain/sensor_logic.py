from typing import List
from typing import Sequence
from app.models.sensor import SensorData, SensorDataIn
from app.infrastructure.database.sensor_repository import (
    fetch_latest_sensor_data,
    insert_sensor_record,
)
from app.infrastructure.database.transaction import run_in_transaction


async def get_latest_sensor_data(limit: int = 100) -> Sequence[SensorData]:
    from app.infrastructure.database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        return await fetch_latest_sensor_data(db, limit)


async def create_sensor_data(data: SensorDataIn) -> SensorData:
    async with run_in_transaction() as db:
        return await insert_sensor_record(db, data)
