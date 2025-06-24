from fastapi import APIRouter,Request
from fastapi.responses import JSONResponse
from loguru import logger
from app.utils.exceptions_base import AppException
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
    try:
        sensor = await get_sensor_by_id(payload.sensor_id)
        logger.info("[SENSOR_META] Retrieved sensor | id=%s", payload.sensor_id)
        return sensor
    except Exception as e:
        logger.exception("[SENSOR_META] Failed to fetch sensor | id=%s", payload.sensor_id)
        raise AppException.from_internal_error("Failed to find sensor", domain="sensor")



@router.get("/", response_model=list[SensorOut])
@limiter.limit(settings.SENSOR_META_QUERY_RATE_LIMIT)
async def list_all_sensors(request: Request):
    try:
        sensors = await list_sensors()
        logger.info("[SENSOR_META] Listed all sensors | count=%d", len(sensors))
        return sensors
    except Exception as e:
        logger.exception("[SENSOR_META] Failed to list sensors")
        raise AppException.from_internal_error("Failed to list all sensors", domain="sensor")



@router.get("/unregistered", response_model=list[SensorOut])
@limiter.limit(settings.SENSOR_META_QUERY_RATE_LIMIT)
async def list_unregistered_sensors(request: Request):
    try:
        sensors = await list_sensors_with_placeholder()
        logger.info("[SENSOR_META] Listed unregistered sensors | count=%d", len(sensors))
        return sensors
    except Exception as e:
        logger.exception("[SENSOR_META] Failed to list unregistered sensors")
        raise AppException.from_internal_error("Failed to list unregistered sensors", domain="sensor")


# ──────────────── Admin/Write Endpoints ───────────── #

@router.put("/admin/update", response_model=SensorOut)
@limiter.limit(settings.SENSOR_META_ADMIN_RATE_LIMIT)
async def update_sensor_entry(request: Request, payload: SensorUpdatePayload):
    try:
        updated = await update_sensor(payload.sensor_id, payload.update)
        logger.info("[SENSOR_META] Updated sensor | id=%s", payload.sensor_id)
        return updated
    except Exception as e:
        logger.exception("[SENSOR_META] Failed to update sensor | id=%s", payload.sensor_id)
        raise AppException.from_internal_error("Failed to update sensor metadata", domain="sensor")


@router.delete("/admin", status_code=204)
@limiter.limit(settings.SENSOR_META_ADMIN_RATE_LIMIT)
async def delete_sensor_entry(request: Request, payload: SensorIdPayload):
    try:
        await delete_sensor(payload.sensor_id)
        logger.info("[SENSOR_META] Deleted sensor | id=%s", payload.sensor_id)
    except Exception as e:
        logger.exception("[SENSOR_META] Failed to delete sensor | id=%s", payload.sensor_id)
        raise AppException.from_internal_error("Failed to delete sensor", domain="sensor")



# ──────────────── System Monitoring ───────────────── #

@router.get("/mqtt-status", summary="Get current status of MQTT listener")
@limiter.limit(settings.SENSOR_MQTT_MONITOR_RATE_LIMIT)
async def get_mqtt_listener_status(request: Request):
    try:
        logger.info("[SENSOR_META] MQTT status requested")
        return JSONResponse(
            content={
                "status": "running" if mqtt_state.is_running else "not running",
                "last_message_at": mqtt_state.last_message_at.isoformat() if mqtt_state.last_message_at else None,
                "last_device_id": str(mqtt_state.last_device_id) if mqtt_state.last_device_id else None,
                "message_count": mqtt_state.message_count
            }
        )
    except Exception as e:
        logger.exception("[SENSOR_META] Failed to retrieve MQTT status")
        raise AppException.from_internal_error("Failed to retrieve MQTT listener status", domain="sensor")
