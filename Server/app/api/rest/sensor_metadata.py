from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.sensor_schemas import (
    SensorCreate, SensorUpdatePayload, SensorIdPayload, SensorOut
)
from app.domain.sensor_logic import (
    create_sensor, get_sensor_by_id, list_sensors, update_sensor, delete_sensor
)
from app.domain.mqtt_listener import mqtt_state


router = APIRouter(prefix="/sensor/metadata", tags=["Sensor Metadata"])


@router.post("/admin", response_model=SensorOut, status_code=201)
async def create_sensor_entry(data: SensorCreate):
    return await create_sensor(data)


@router.post("/find", response_model=SensorOut)
async def get_sensor(payload: SensorIdPayload):
    return await get_sensor_by_id(payload.sensor_id)


@router.get("", response_model=list[SensorOut])
async def list_all_sensors():
    return await list_sensors()


@router.put("/admin/update", response_model=SensorOut)
async def update_sensor_entry(payload: SensorUpdatePayload):
    return await update_sensor(payload.sensor_id, payload.update)


@router.delete("/admin", status_code=204)
async def delete_sensor_entry(payload: SensorIdPayload):
    await delete_sensor(payload.sensor_id)


@router.get("/mqtt-status", summary="Get current status of MQTT listener")
async def get_mqtt_listener_status():
    return JSONResponse(
        content={
            "status": "running" if mqtt_state.is_running else "not running",
            "last_message_at": mqtt_state.last_message_at.isoformat() if mqtt_state.last_message_at else None,
            "last_device_id": str(mqtt_state.last_device_id) if mqtt_state.last_device_id else None,
            "message_count": mqtt_state.message_count
        }
    )