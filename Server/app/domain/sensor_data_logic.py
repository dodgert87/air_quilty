from uuid import UUID
from app.infrastructure.database.repository import sensor_data_graphql_repository
from app.models.schemas.graphQL.SensorDataAdvancedQuery import SensorDataAdvancedQuery
from app.models.DB_tables.sensor import Sensor
from app.infrastructure.database.repository import sensor_repository
from app.infrastructure.database.repository import sensor_data_repository
from app.domain.pagination import paginate_query
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn, SensorDataOut, SensorQuery, SensorRangeQuery, SensorTimestampQuery
from app.utils.config import settings
from app.utils.exceptions_base import AppException


async def query_sensor_data_by_ranges(payload: SensorRangeQuery):
    query = await sensor_data_repository.search_by_attribute_ranges(payload)
    return await paginate_query(query, page=payload.page, schema=SensorDataOut, page_size=settings.DEFAULT_PAGE_SIZE)


async def create_sensor_data_entry(payload: SensorDataIn):

    return await sensor_data_repository.insert_sensor_data(payload)


async def get_latest_entries_for_sensors(sensor_ids: list[UUID] | None):
    if not sensor_ids:
        sensors: list[Sensor] = await sensor_repository.fetch_all_sensors()
        sensor_ids = [sensor.sensor_id for sensor in sensors]

    valid_ids = []
    for sid in sensor_ids:
        if await sensor_repository.fetch_sensor_by_id(sid):
            valid_ids.append(sid)

    results = []
    for sid in valid_ids:
        entry = await sensor_data_repository.fetch_latest_by_sensor(sid)
        if entry:
            results.append(entry)
    return results


async def query_sensor_data_by_timestamps(payload: SensorTimestampQuery):
    query = await sensor_data_repository.search_by_timestamps(payload)
    return await paginate_query(query, page=payload.page, schema=SensorDataOut, page_size=settings.DEFAULT_PAGE_SIZE)


async def get_all_data_by_sensor(payload: SensorQuery):
    sensor = await sensor_repository.fetch_sensor_by_id(payload.sensor_id)
    if not sensor:
        raise AppException(
            message=f"Sensor ID {payload.sensor_id} not found",
            status_code=404,
            public_message="Sensor not found",
            domain="sensor"
        )

    query = await sensor_data_repository.search_by_sensor_id(payload.sensor_id)
    return await paginate_query(query, schema=SensorDataOut, page=payload.page, page_size=settings.DEFAULT_PAGE_SIZE)


async def query_sensor_data_advanced(payload: SensorDataAdvancedQuery):
    query = await sensor_data_graphql_repository.build_sensor_data_query(payload)
    return await paginate_query(query, page=payload.page, schema=SensorDataOut, page_size=payload.page_size or settings.DEFAULT_PAGE_SIZE)