from uuid import UUID
from app.models.sensor import Sensor
from app.infrastructure.database import sensor_repository
from app.infrastructure.database import sensor_data_repository
from app.domain.pagination import paginate_query
from app.infrastructure.database.sensor_data_repository import fetch_latest_by_sensor, search_by_attribute_ranges, search_by_sensor_id, search_by_timestamps
from app.models.sensor_data_schemas import SensorDataIn, SensorDataOut, SensorQuery, SensorRangeQuery, SensorTimestampQuery
from app.utils.config import settings


async def query_sensor_data_by_ranges(payload: SensorRangeQuery):
    query = await search_by_attribute_ranges(payload) # type: ignore
    return await paginate_query(query, page=payload.page,schema=SensorDataOut ,page_size=settings.DEFAULT_PAGE_SIZE)

async def create_sensor_data_entry(payload: SensorDataIn):
    sensor = await sensor_repository.fetch_sensor_by_id(payload.device_id)
    if not sensor:
        raise  ValueError("Sensor with the given device_id does not exist")

    return await sensor_data_repository.insert_sensor_data(payload)

async def get_latest_entries_for_sensors(sensor_ids: list[UUID] | None):
    if not sensor_ids:
        sensors: list[Sensor] = await sensor_repository.fetch_all_sensors()
        sensor_ids = [sensor.id for sensor in sensors]

    valid_ids = []
    for sid in sensor_ids:
        if await sensor_repository.fetch_sensor_by_id(sid):
            valid_ids.append(sid)

    results = []
    for sid in valid_ids:
        entry = await fetch_latest_by_sensor(sid)
        if entry:
            results.append(entry)
    return results

async def query_sensor_data_by_timestamps(payload: SensorTimestampQuery):
    try:
        query = await search_by_timestamps(payload)
        return await paginate_query(query, page=payload.page,schema=SensorDataOut, page_size=settings.DEFAULT_PAGE_SIZE)
    except Exception as e:
        raise ValueError(f"Error querying by timestamps: {e}")

async def get_all_data_by_sensor(payload: SensorQuery):
    sensor = await sensor_repository.fetch_sensor_by_id(payload.sensor_id)
    if not sensor:
        return ValueError("Sensor with the given ID does not exist")

    query = await search_by_sensor_id(payload.sensor_id)
    return await paginate_query(query,schema=SensorDataOut ,page=payload.page, page_size=settings.DEFAULT_PAGE_SIZE)