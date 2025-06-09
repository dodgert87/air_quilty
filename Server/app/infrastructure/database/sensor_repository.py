from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from app.models.sensor import Sensor
from app.infrastructure.database.transaction import run_in_transaction
from app.models.sensor_schemas import SensorCreate, SensorUpdate


async def insert_sensor(sensor_data: SensorCreate) -> Sensor:
    try:
        async with run_in_transaction() as session:
            sensor = Sensor(**sensor_data.model_dump())
            session.add(sensor)
            return sensor
    except SQLAlchemyError as e:
        raise


async def fetch_sensor_by_id(sensor_id: UUID) -> Sensor | None:
    try:
        async with run_in_transaction() as session:
            return await session.get(Sensor, sensor_id)
    except SQLAlchemyError as e:
        raise


async def fetch_all_sensors() -> list[Sensor]:
    try:
        async with run_in_transaction() as session:
            result = await session.execute(select(Sensor).order_by(Sensor.created_at.desc()))
            return list(result.scalars().all())
    except SQLAlchemyError as e:
        raise


async def modify_sensor(sensor_id: UUID, update_data: SensorUpdate) -> Sensor | None:
    try:
        async with run_in_transaction() as session:
            sensor = await session.get(Sensor, sensor_id)
            if not sensor:
                return None
            for field, value in update_data.model_dump(exclude_unset=True).items():
                setattr(sensor, field, value)
            sensor.updated_at = datetime.now(timezone.utc)
            return sensor
    except SQLAlchemyError as e:
        raise


async def remove_sensor(sensor_id: UUID) -> bool:
    try:
        async with run_in_transaction() as session:
            sensor = await session.get(Sensor, sensor_id)
            if not sensor:
                return False
            await session.delete(sensor)
            return True
    except SQLAlchemyError as e:
        raise
