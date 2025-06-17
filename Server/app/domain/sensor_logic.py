from typing import List
from uuid import UUID
from app.domain.pagination import paginate_query
from app.infrastructure.database.repository.graphQL.sensor_metadata_graphql_repository import sensor_metadata_graphql_repository
from app.models.schemas.graphQL.sensor_meta_data_query import SensorMetadataQuery
from app.models.DB_tables.sensor import Sensor
from app.models.schemas.rest.sensor_schemas import SensorCreate, SensorOut, SensorUpdate
from app.infrastructure.database.repository.restAPI import sensor_repository
from app.utils.exceptions_base import SensorNotFoundError
from app.utils.config import settings

async def create_sensor(sensor_data: SensorCreate):
    return await sensor_repository.insert_sensor(sensor_data)


async def get_sensor_by_id(sensor_id: UUID):
    sensor = await sensor_repository.fetch_sensor_by_id(sensor_id)
    if not sensor:
        raise SensorNotFoundError(sensor_id)
    return sensor

async def safe_get_sensor_by_id(sensor_id: UUID) -> Sensor | None:
    try:
        return await get_sensor_by_id(sensor_id)
    except SensorNotFoundError:
        return None

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

async def list_sensors_with_placeholder() -> list[SensorOut]:
    all_sensors = await sensor_repository.fetch_all_sensors()
    return [
        SensorOut.model_validate(s)
        for s in all_sensors
        if s.name == "UNKNOWN"
    ]

async def query_sensor_metadata_advanced(payload: SensorMetadataQuery):
    query = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    return await paginate_query(
        query,
        page=payload.page,
        schema=SensorOut,
        page_size=payload.page_size or settings.DEFAULT_PAGE_SIZE
    )