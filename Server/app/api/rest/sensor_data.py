from typing import List
from fastapi import APIRouter, Request
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
    """Fetch the latest data entries for a list of sensor IDs."""
    return await get_latest_entries_for_sensors(payload.sensor_ids)


# ──────────────── Sensor Querying ───────────────────── #

@router.post("/by-ranges", response_model=PaginatedResponse[SensorDataPartialOut], response_model_exclude_none=True)
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_sensor_data_by_ranges(request: Request, payload: SensorRangeQuery):
    """Query sensor data filtered by field ranges (e.g. temperature > X)."""
    return await query_sensor_data_by_ranges(payload)


@router.post("/by-timestamps", response_model=PaginatedResponse)
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_sensor_data_by_timestamps(request: Request, payload: SensorTimestampQuery):
    """Query sensor data using timestamps or timestamp ranges."""
    return await query_sensor_data_by_timestamps(payload) # type: ignore


@router.post("/by-sensor", response_model=PaginatedResponse[SensorDataOut])
@limiter.limit(settings.SENSOR_QUERY_RATE_LIMIT)
async def get_data_by_sensor(request: Request, payload: SensorQuery):
    """Fetch all data for a given sensor, optionally paginated."""
    return await get_all_data_by_sensor(payload)


# ──────────────── Sensor Data Ingestion ─────────────── #

@router.post("/", response_model=SensorDataOut, status_code=201)
@limiter.limit(settings.SENSOR_CREATE_RATE_LIMIT)
async def add_sensor_data(request: Request, payload: SensorDataIn):
    """Create a new sensor data record in the database."""
    return await create_sensor_data_entry(payload)
