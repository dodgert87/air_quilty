from uuid import UUID
from app.models.sensor_schemas import SensorCreate, SensorUpdate
from app.infrastructure.database import sensor_repository
from app.utils.exceptions_base import SensorNotFoundError


async def create_sensor(sensor_data: SensorCreate):
    return await sensor_repository.insert_sensor(sensor_data)


async def get_sensor_by_id(sensor_id: UUID):
    sensor = await sensor_repository.fetch_sensor_by_id(sensor_id)
    if not sensor:
        raise SensorNotFoundError(sensor_id)
    return sensor


async def list_sensors():
    return await sensor_repository.fetch_all_sensors()


async def update_sensor(sensor_id: UUID, update_data: SensorUpdate):
    sensor = await sensor_repository.modify_sensor(sensor_id, update_data)
    if not sensor:
        raise SensorNotFoundError(sensor_id)
    return sensor


async def delete_sensor(sensor_id: UUID):
    success = await sensor_repository.remove_sensor(sensor_id)
    if not success:
        raise SensorNotFoundError(sensor_id)
    return True
