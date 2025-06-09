from fastapi import APIRouter, HTTPException
from app.models.sensor_schemas import SensorCreate, SensorUpdate, SensorOut
from app.domain.sensor_logic import (
    create_sensor,
    get_sensor_by_id,
    list_sensors,
    update_sensor,
    delete_sensor
)

router = APIRouter(prefix="/sensor/metadata", tags=["Sensor Metadata"])


@router.post("/", response_model=SensorOut, status_code=201)
async def create_sensor_entry(data: SensorCreate):
    sensor = await create_sensor(data)
    return sensor


@router.get("/{sensor_id}", response_model=SensorOut)
async def get_sensor(sensor_id: str):
    sensor = await get_sensor_by_id(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.get("", response_model=list[SensorOut])
async def list_all_sensors():
    return await list_sensors()


@router.put("/{sensor_id}", response_model=SensorOut)
async def update_sensor_entry(sensor_id: str, update: SensorUpdate):
    updated = await update_sensor(sensor_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return updated


@router.delete("/{sensor_id}", status_code=204)
async def delete_sensor_entry(sensor_id: str):
    deleted = await delete_sensor(sensor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return
