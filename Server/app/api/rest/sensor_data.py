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

@router.post("/latest", response_model=List[SensorDataOut])
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

@router.post("/by-ranges", response_model=PaginatedResponse[SensorDataPartialOut], response_model_exclude_none=True)
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_sensor_data_by_ranges(request: Request, payload: SensorRangeQuery):
    try:
        result = await query_sensor_data_by_ranges(payload)
        logger.info("[SENSOR] Range query | total=%d | page=%d", result.total, result.page)
        return result
    except Exception as e:
        logger.exception("[SENSOR] Range query failed | payload=%s", payload)
        raise AppException.from_internal_error("Failed to query sensor data by range", domain="sensor")



@router.post("/by-timestamps", response_model=PaginatedResponse)
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_sensor_data_by_timestamps(request: Request, payload: SensorTimestampQuery):
    try:
        result = await query_sensor_data_by_timestamps(payload)
        logger.info("[SENSOR] Timestamp query | total=%d | page=%d", result.total, result.page)
        return result
    except Exception as e:
        logger.exception("[SENSOR] Timestamp query failed | payload=%s", payload)
        raise AppException.from_internal_error("Failed to query sensor data by timestamps", domain="sensor")



@router.post("/by-sensor", response_model=PaginatedResponse[SensorDataOut])
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_data_by_sensor(request: Request, payload: SensorQuery):
    try:
        result = await get_all_data_by_sensor(payload)
        logger.info("[SENSOR] Sensor data fetch | sensor_id=%s | total=%d", payload.sensor_id, result.total)
        return result
    except Exception as e:
        logger.exception("[SENSOR] Sensor fetch failed | payload=%s", payload)
        raise AppException.from_internal_error("Failed to fetch sensor data", domain="sensor")



# ──────────────── Sensor Data Ingestion ─────────────── #

@router.post("/", response_model=SensorDataOut, status_code=201)
@limiter.limit(settings.SENSOR_CREATE_RATE_LIMIT)
async def add_sensor_data(request: Request, payload: SensorDataIn):
    try:
        result = await create_sensor_data_entry(payload)
        logger.info("[SENSOR] Created sensor entry | sensor_id=%s | timestamp=%s", result.id, result.timestamp)
        return result
    except Exception as e:
        logger.exception("[SENSOR] Failed to create sensor data entry | payload=%s", payload)
        raise AppException.from_internal_error("Failed to store sensor data", domain="sensor")
