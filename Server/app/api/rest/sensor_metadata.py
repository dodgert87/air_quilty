from fastapi import APIRouter,Request
from fastapi.responses import JSONResponse
from app.models.schemas.rest.sensor_schemas import (
    SensorUpdatePayload, SensorIdPayload, SensorOut
)
from app.domain.sensor_logic import (
    get_sensor_by_id, list_sensors, list_sensors_with_placeholder,
    update_sensor, delete_sensor
)
from app.domain.mqtt_listener import mqtt_state
from app.middleware.rate_limit_middleware import limiter
from app.utils.config import settings

router = APIRouter(prefix="/sensor/metadata", tags=["Sensor Metadata"])

# ──────────────── Public/Query Endpoints ───────────── #

@router.post("/find", response_model=SensorOut)
@limiter.limit(settings.SENSOR_META_QUERY_RATE_LIMIT)
async def get_sensor(request: Request, payload: SensorIdPayload):
    """Find a sensor by its unique ID."""
    return await get_sensor_by_id(payload.sensor_id)


@router.get("", response_model=list[SensorOut])
@limiter.limit(settings.SENSOR_META_QUERY_RATE_LIMIT)
async def list_all_sensors(request: Request):
    """List all registered sensors (active or inactive)."""
    return await list_sensors()


@router.get("/unregistered", response_model=list[SensorOut])
@limiter.limit(settings.SENSOR_META_QUERY_RATE_LIMIT)
async def list_unregistered_sensors(request: Request):
    """Returns all sensors that are auto-registered and pending admin update."""
    return await list_sensors_with_placeholder()


# ──────────────── Admin/Write Endpoints ───────────── #

@router.put("/admin/update", response_model=SensorOut)
@limiter.limit(settings.SENSOR_META_ADMIN_RATE_LIMIT)
async def update_sensor_entry(request: Request, payload: SensorUpdatePayload):
    """Update metadata fields of a registered sensor (Admin only)."""
    return await update_sensor(payload.sensor_id, payload.update)


@router.delete("/admin", status_code=204)
@limiter.limit(settings.SENSOR_META_ADMIN_RATE_LIMIT)
async def delete_sensor_entry(request: Request, payload: SensorIdPayload):
    """Delete a sensor from the registry (Admin only)."""
    await delete_sensor(payload.sensor_id) # type: ignore


# ──────────────── System Monitoring ───────────────── #

@router.get("/mqtt-status", summary="Get current status of MQTT listener")
@limiter.limit(settings.SENSOR_MQTT_MONITOR_RATE_LIMIT)
async def get_mqtt_listener_status(request: Request):
    """Return the current status of the MQTT listener and its latest activity."""
    return JSONResponse(
        content={
            "status": "running" if mqtt_state.is_running else "not running",
            "last_message_at": mqtt_state.last_message_at.isoformat() if mqtt_state.last_message_at else None,
            "last_device_id": str(mqtt_state.last_device_id) if mqtt_state.last_device_id else None,
            "message_count": mqtt_state.message_count
        }
    )
