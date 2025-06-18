from typing import List
from fastapi import APIRouter
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

router = APIRouter(prefix="/sensor/data", tags=["Sensor Data"])


@router.post("/by-ranges", response_model=PaginatedResponse[SensorDataPartialOut], response_model_exclude_none=True)
async def get_sensor_data_by_ranges(payload: SensorRangeQuery):
    return await query_sensor_data_by_ranges(payload)


@router.post("/", response_model=SensorDataOut, status_code=201)
async def add_sensor_data(payload: SensorDataIn):
    return await create_sensor_data_entry(payload)


@router.post("/latest", response_model=List[SensorDataOut])
async def get_latest_sensor_data(payload: SensorListInput):
    return await get_latest_entries_for_sensors(payload.sensor_ids)


@router.post("/by-timestamps", response_model=PaginatedResponse)
async def get_sensor_data_by_timestamps(payload: SensorTimestampQuery):
    return await query_sensor_data_by_timestamps(payload)


@router.post("/by-sensor", response_model=PaginatedResponse[SensorDataOut])
async def get_data_by_sensor(payload: SensorQuery):
    return await get_all_data_by_sensor(payload)
