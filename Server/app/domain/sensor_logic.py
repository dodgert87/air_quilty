from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from app.models.sensor import Sensor
from app.infrastructure.database.transaction import run_in_transaction
from app.models.sensor_schemas import SensorCreate, SensorUpdate


async def create_sensor(sensor_data: SensorCreate) -> Sensor:
    async with run_in_transaction() as session:
        sensor = Sensor(**sensor_data.dict())
        session.add(sensor)
        return sensor


async def get_sensor_by_id(sensor_id: str) -> Sensor | None:
    async with run_in_transaction() as session:
        result = await session.get(Sensor, sensor_id)
        return result


async def list_sensors() -> list[Sensor]:
    async with run_in_transaction() as session:
        result = await session.execute(select(Sensor).order_by(Sensor.created_at.desc()))
        return list(result.scalars().all())


async def update_sensor(sensor_id: str, update_data: SensorUpdate) -> Sensor | None:
    async with run_in_transaction() as session:
        existing = await session.get(Sensor, sensor_id)
        if not existing:
            return None
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(existing, field, value)
        return existing


async def delete_sensor(sensor_id: str) -> bool:
    async with run_in_transaction() as session:
        result = await session.get(Sensor, sensor_id)
        if not result:
            return False
        await session.delete(result)
        return True
