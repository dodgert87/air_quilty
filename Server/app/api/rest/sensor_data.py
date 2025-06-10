from typing import List
from fastapi import APIRouter, HTTPException, Query
from app.domain.sensor_data_logic import create_sensor_data_entry, get_all_data_by_sensor, get_latest_entries_for_sensors, query_sensor_data_by_ranges, query_sensor_data_by_timestamps
from app.models.sensor_data_schemas import SensorDataIn, SensorListInput, SensorQuery, SensorRangeQuery, SensorDataOut, SensorTimestampQuery
from app.domain.pagination import PaginatedResponse

router = APIRouter(prefix="/sensor/data", tags=["Sensor Data"])


@router.post("/by-ranges", response_model=PaginatedResponse)
async def get_sensor_data_by_ranges(payload: SensorRangeQuery):
    try:
        return await query_sensor_data_by_ranges(payload)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error")

@router.post("/", response_model=SensorDataOut, status_code=201)
async def add_sensor_data(payload: SensorDataIn):
    try:
        return await create_sensor_data_entry(payload)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception :
        raise HTTPException(status_code=500, detail="Failed to insert sensor data")

@router.post("/latest", response_model=List[SensorDataOut])
async def get_latest_sensor_data(payload: SensorListInput):
    entries = await get_latest_entries_for_sensors(payload.sensor_ids)
    if not entries:
        raise HTTPException(status_code=404, detail="No latest entries found.")
    return entries

@router.post("/by-timestamps")
async def get_sensor_data_by_timestamps(payload: SensorTimestampQuery):
    try:
        return await query_sensor_data_by_timestamps(payload)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error while fetching sensor data by timestamps")

@router.post("/by-sensor", response_model=PaginatedResponse[SensorDataOut])
async def get_data_by_sensor(payload: SensorQuery):
    return await get_all_data_by_sensor(payload)
