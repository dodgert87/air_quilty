from uuid import UUID
from app.infrastructure.database.repository.graphQL import sensor_data_graphql_repository
from app.models.schemas.graphQL.Sensor_data_query import SensorDataAdvancedQuery
from app.models.DB_tables.sensor import Sensor
from app.infrastructure.database.repository.restAPI import sensor_repository
from app.infrastructure.database.repository.restAPI import sensor_data_repository
from app.domain.pagination import paginate_query
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn, SensorDataOut, SensorDataPartialOut, SensorQuery, SensorRangeQuery, SensorTimestampQuery
from app.utils.config import settings
from app.utils.exceptions_base import AppException
from loguru import logger



async def query_sensor_data_by_ranges(payload: SensorRangeQuery):
    """
    Query sensor data using field-level value ranges.
    Applies pagination and returns partial schema for efficiency.
    """
    logger.info("[SENSOR_DATA] Range query | fields=%s | page=%d", payload.ranges, payload.page)
    query = await sensor_data_repository.search_by_attribute_ranges(payload)
    return await paginate_query(query, page=payload.page, schema=SensorDataPartialOut, page_size=settings.DEFAULT_PAGE_SIZE)


async def create_sensor_data_entry(payload: SensorDataIn) -> SensorDataOut:
    """
    Insert a new sensor data row into the database.

    Args:
        payload (SensorDataIn): Sensor data payload.

    Returns:
        SensorDataOut: The stored and validated response object.
    """
    db_obj = await sensor_data_repository.insert_sensor_data(payload)
    logger.info("[SENSOR_DATA] Created data entry | sensor_id=%s | ts=%s", payload.device_id, payload.timestamp)
    return SensorDataOut.model_validate(db_obj)


async def get_latest_entries_for_sensors(sensor_ids: list[UUID] | None):
    """
    Return the most recent sensor data entry for each sensor in the provided list.
    If no list is provided, fetches entries for all known sensors.

    Returns:
        list[SensorDataOut]: One per sensor.
    """
    if not sensor_ids:
        sensors = await sensor_repository.fetch_all_sensors()
        sensor_ids = [sensor.sensor_id for sensor in sensors]
        logger.info("[SENSOR_DATA] No sensor_ids provided, defaulting to all (%d)", len(sensor_ids))

    valid_ids = []
    for sid in sensor_ids:
        if await sensor_repository.fetch_sensor_by_id(sid):
            valid_ids.append(sid)
        else:
            logger.warning("[SENSOR_DATA] Skipping invalid sensor ID: %s", sid)

    results = []
    for sid in valid_ids:
        entry = await sensor_data_repository.fetch_latest_by_sensor(sid)
        if entry:
            results.append(entry)

    logger.info("[SENSOR_DATA] Fetched latest entries | sensors=%d | results=%d", len(valid_ids), len(results))
    return results



async def query_sensor_data_by_timestamps(payload: SensorTimestampQuery):
    """
    Query sensor data using either exact or ranged timestamps.
    Uses pagination and returns full schema.
    """
    logger.info("[SENSOR_DATA] Timestamp query | timestamps=%s | exact=%s | page=%d", payload.timestamps, payload.exact, payload.page)
    query = await sensor_data_repository.search_by_timestamps(payload)
    return await paginate_query(query, page=payload.page, schema=SensorDataOut, page_size=settings.DEFAULT_PAGE_SIZE)


async def get_all_data_by_sensor(payload: SensorQuery):
    """
    Get paginated data for a specific sensor by ID.

    Raises:
        AppException: If sensor doesn't exist.
    """
    sensor = await sensor_repository.fetch_sensor_by_id(payload.sensor_id)
    if not sensor:
        logger.warning("[SENSOR_DATA] Sensor not found | id=%s", payload.sensor_id)
        raise AppException(
            message=f"Sensor ID {payload.sensor_id} not found",
            status_code=404,
            public_message="Sensor not found",
            domain="sensor"
        )

    logger.info("[SENSOR_DATA] Querying all data for sensor | id=%s | page=%d", payload.sensor_id, payload.page)
    query = await sensor_data_repository.search_by_sensor_id(payload.sensor_id)
    return await paginate_query(query, schema=SensorDataOut, page=payload.page, page_size=settings.DEFAULT_PAGE_SIZE)


async def query_sensor_data_advanced(payload: SensorDataAdvancedQuery):
    """
    Advanced GraphQL-style query using multiple optional filters:
    - Timestamp range
    - Sensor ID(s)
    - Metadata filters (location, model)
    - Field value filters

    Returns paginated results as SensorDataOut objects.
    """
    logger.info("[SENSOR_DATA] Advanced GraphQL query | query=%s | page=%d", payload.model_dump(), payload.page)
    query = await sensor_data_graphql_repository.build_sensor_data_query(payload)
    return await paginate_query(query, page=payload.page, schema=SensorDataOut, page_size=payload.page_size or settings.DEFAULT_PAGE_SIZE)
