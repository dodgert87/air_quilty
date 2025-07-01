from typing import List
from fastapi import APIRouter, Request
from loguru import logger
from app.utils.exceptions_base import AppException
from app.domain.sensor_data_logic import (
    create_sensor_data_entry,
    get_all_data_by_sensor,
    get_latest_entries_for_sensors,
    query_sensor_data_by_ranges,
    query_sensor_data_by_timestamps,
)
from app.models.schemas.rest.sensor_data_schemas import (
    SensorDataIn,
    SensorDataPartialOut,
    SensorListInput,
    SensorQuery,
    SensorRangeQuery,
    SensorDataOut,
    SensorTimestampQuery,
)
from app.domain.pagination import PaginatedResponse
from app.middleware.rate_limit_middleware import limiter
from app.utils.config import settings

router = APIRouter(prefix="/sensor/data", tags=["Sensor Data"])

# ──────────────── Public/Unauthenticated ───────────── #

@router.post(
    "/latest",
    response_model=List[SensorDataOut],
    tags=["Sensor Data"],
    summary="Get latest sensor readings",
    description=f"""
Returns the most recent data entries for each sensor in the list.
This endpoint is publicly accessible (no authentication required).
Rate limited: {settings.SENSOR_PUBLIC_RATE_LIMIT}
"""
)
@limiter.limit(settings.SENSOR_PUBLIC_RATE_LIMIT)
async def get_latest_sensor_data(request: Request, payload: SensorListInput):
    try:
        result = await get_latest_entries_for_sensors(payload.sensor_ids)
        logger.info("[SENSOR] Fetched latest entries | count=%d", len(result))
        return result
    except Exception as e:
        logger.exception("[SENSOR] Failed to fetch latest sensor entries | sensor_ids=%s", payload.sensor_ids)
        raise AppException.from_internal_error("Failed to fetch latest sensor data", domain="sensor")


# ──────────────── Sensor Querying ───────────────────── #

@router.post(
    "/by-ranges",
    response_model=PaginatedResponse[SensorDataPartialOut],
    response_model_exclude_none=True,
    tags=["Sensor Data"],
    summary="Query sensor data by field value ranges",
    description=f"""
Returns paginated sensor readings filtered by numeric [min, max] bounds for any field,
Use `null` to represent infinity (i.e., no bound).
Authentication is required via API Key.
Rate limited: {settings.SENSOR_QUERY_RATE_LIMIT}
"""
)
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_sensor_data_by_ranges(request: Request, payload: SensorRangeQuery):
    try:
        result = await query_sensor_data_by_ranges(payload)
        logger.info("[SENSOR] Range query | total=%d | page=%d", result.total, result.page)
        return result
    except Exception as e:
        logger.exception("[SENSOR] Range query failed | payload=%s", payload)
        raise AppException.from_internal_error("Failed to query sensor data by range", domain="sensor")




@router.post(
    "/by-timestamps",
    response_model=PaginatedResponse,
    tags=["Sensor Data"],
    summary="Query sensor data by timestamps",
    description=f"""
Returns paginated sensor readings that match either exact list of timestamps
or fall within the inclusive time range if exact if false, must give only two timestamps.
Authentication is required via API Key.
Rate limited: {settings.SENSOR_QUERY_RATE_LIMIT}
"""
)
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_sensor_data_by_timestamps(request: Request, payload: SensorTimestampQuery):
    try:
        result = await query_sensor_data_by_timestamps(payload)
        logger.info("[SENSOR] Timestamp query | total=%d | page=%d", result.total, result.page)
        return result
    except Exception as e:
        logger.exception("[SENSOR] Timestamp query failed | payload=%s", payload)
        raise AppException.from_internal_error("Failed to query sensor data by timestamps", domain="sensor")



@router.post(
    "/by-sensor",
    response_model=PaginatedResponse[SensorDataOut],
    tags=["Sensor Data"],
    summary="Query sensor data by sensor UUID",
    description=f"""
Returns all readings from a specific sensor, paginated by timestamp.
Authentication is required via API Key.
Rate limited: {settings.SENSOR_QUERY_RATE_LIMIT}
"""
)
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_data_by_sensor(request: Request, payload: SensorQuery):
    try:
        result = await get_all_data_by_sensor(payload)
        logger.info("[SENSOR] Sensor data fetch | sensor_id=%s | total=%d", payload.sensor_id, result.total)
        return result
    except Exception as e:
        logger.exception("[SENSOR] Sensor fetch failed | payload=%s", payload)
        raise AppException.from_internal_error("Failed to fetch sensor data", domain="sensor")



