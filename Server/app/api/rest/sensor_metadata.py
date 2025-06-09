from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.models.sensor_schemas import (
    SensorCreate, SensorUpdatePayload, SensorIdPayload, SensorOut
)
from app.domain.sensor_logic import (
    create_sensor, get_sensor_by_id, list_sensors, update_sensor, delete_sensor
)

router = APIRouter(prefix="/sensor/metadata", tags=["Sensor Metadata"])


@router.post("/admin", response_model=SensorOut, status_code=201)
async def create_sensor_entry(data: SensorCreate):
    try:
        return await create_sensor(data)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create sensor")


@router.post("/find", response_model=SensorOut)
async def get_sensor(payload: SensorIdPayload):
    try:
        return await get_sensor_by_id(payload.sensor_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Sensor not found")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("", response_model=list[SensorOut])
async def list_all_sensors():
    try:
        return await list_sensors()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.put("/admin/update", response_model=SensorOut)
async def update_sensor_entry(payload: SensorUpdatePayload):
    try:
        return await update_sensor(payload.sensor_id, payload.update)
    except ValueError:
        raise HTTPException(status_code=404, detail="Sensor not found")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")


@router.delete("/admin", status_code=204)
async def delete_sensor_entry(payload: SensorIdPayload):
    try:
        await delete_sensor(payload.sensor_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Sensor not found")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")
