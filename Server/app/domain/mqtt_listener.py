# mqtt_listener.py
import asyncio
import json
import traceback
from datetime import datetime, timezone
from uuid import UUID
from aiomqtt import Client, MqttError
from loguru import logger
from pydantic import ValidationError

from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.dispatcher import dispatcher
from app.domain.sensor_logic import create_sensor, safe_get_sensor_by_id
from app.domain.sensor_data_logic import create_sensor_data_entry
from app.infrastructure.database.repository.restAPI.sensor_repository import modify_sensor
from app.models.schemas.rest.sensor_schemas import SensorCreate, SensorOut, SensorUpdate
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn, SensorDataOut
from app.utils.config import settings


class MQTTListenerState:
    """
    Tracks internal metrics of the MQTT listener.
    """
    is_running: bool = False
    last_message_at: datetime | None = None
    last_device_id: UUID | None = None
    message_count: int = 0


mqtt_state = MQTTListenerState()


async def process_status_message(topic: str, text: str):
    """
    Process a sensor's connection status message.

    Expected topic format: A3/AirQuality/Connection/<sensor_id>
    Payload is expected to be either "online" or "offline".
    """
    sensor_id_str = topic.split("/")[-1]
    try:
        sensor_id = UUID(sensor_id_str)
    except ValueError:
        logger.warning(f"Invalid UUID in connection topic: {sensor_id_str}")
        return

    is_active = text.strip().lower() == "online"

    if not await ensure_sensor_exists(sensor_id, is_active=is_active):
        update_data = SensorUpdate(is_active=is_active)  # type: ignore
        sensor = await modify_sensor(sensor_id, update_data)
        if sensor:
            sensor_out = SensorOut.model_validate(sensor)
            await dispatcher.dispatch(WebhookEvent.SENSOR_STATUS_CHANGED, sensor_out)
            logger.info(f"Updated sensor {sensor_id} status to {'active' if is_active else 'inactive'} via MQTT")


async def process_sensor_data(text: str):
    """
    Process and store sensor data received from MQTT.

    If sensor does not exist, creates a placeholder.
    Dispatches webhook events for:
    - SENSOR_DATA_RECEIVED
    - ALERT_TRIGGERED
    """
    payload_dict = json.loads(text)
    logger.debug(f"MQTT payload parsed: {payload_dict}")
    data = SensorDataIn(**payload_dict)

    logger.info("[MQTT] Processing sensor data | device_id=%s", data.device_id)

    if not await ensure_sensor_exists(data.device_id):
        placeholder = SensorCreate(
            sensor_id=data.device_id,
            name="UNKNOWN",
            location="PENDING",
            model="GENERIC",
            is_active=True
        )
        await create_sensor(placeholder)  # type: ignore
        logger.info("[MQTT] Created placeholder sensor | sensor_id=%s", data.device_id)

    stored: SensorDataOut = await create_sensor_data_entry(data)
    await dispatcher.dispatch(WebhookEvent.SENSOR_DATA_RECEIVED, stored)
    await dispatcher.dispatch(WebhookEvent.ALERT_TRIGGERED, stored)

    logger.info("[MQTT] Dispatched SENSOR_DATA_RECEIVED and ALERT_TRIGGERED | sensor_id=%s", data.device_id)

    # Update local state
    mqtt_state.is_running = True
    mqtt_state.last_message_at = datetime.now(timezone.utc)
    mqtt_state.last_device_id = data.device_id
    mqtt_state.message_count += 1



async def ensure_sensor_exists(sensor_id: UUID, is_active: bool | None = None) -> bool:
    """
    Check if a sensor exists in DB, and if its active status matches expectation.

    Returns:
        bool: True if sensor is valid and no action needed.
    """
    sensor = await safe_get_sensor_by_id(sensor_id)

    if not sensor:
        logger.debug(f"[MQTT] Sensor {sensor_id} not found. Skipping (creation handled elsewhere).")
        return False

    if is_active is not None and sensor.is_active != is_active:
        logger.info("[MQTT] Sensor %s found but active state mismatch: DB=%s vs MQTT=%s", sensor_id, sensor.is_active, is_active)
        return False

    return True



async def handle_mqtt_message(topic: str, payload: bytes | str | memoryview):
    """
    Decode and dispatch the MQTT message based on topic.

    Supports both:
    - Status messages (`A3/AirQuality/Connection/...`)
    - Sensor data messages (default)
    """
    if isinstance(payload, (bytes, bytearray)):
        text = payload.decode()
    elif isinstance(payload, memoryview):
        text = payload.tobytes().decode()
    elif isinstance(payload, str):
        text = payload
    else:
        logger.warning(f"Unsupported MQTT payload type {type(payload)}; skipping")
        return

    logger.info("[MQTT] Message received | topic=%s", topic)

    if topic.startswith(settings.MQTT_SENSOR_STATUS_TOPICSt_START_WITH):
        await process_status_message(topic, text)
    else:
        await process_sensor_data(text)



async def listen_to_mqtt() -> None:
    """
    Long-running async loop that listens to MQTT messages and dispatches handlers.

    Features:
    - Auto reconnect
    - Topic subscription
    - Error-resilient loop with retry
    """
    logger.info("Starting MQTT listener with auto-reconnect…")

    while True:
        try:
            async with Client(
                hostname=settings.MQTT_BROKER,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USERNAME,
                password=settings.MQTT_PASSWORD,
            ) as client:

                await client.subscribe(settings.MQTT_SENSOR_DATA_TOPIC, qos=settings.MQTT_QOS)
                await client.subscribe(settings.MQTT_SENSOR_STATUS_TOPIC, qos=settings.MQTT_QOS)

                logger.info(f"Subscribed to topic: {settings.MQTT_SENSOR_DATA_TOPIC}")
                logger.info(f"Subscribed to topic: {settings.MQTT_SENSOR_STATUS_TOPIC}")

                async for message in client.messages:
                    try:
                        await handle_mqtt_message(message.topic.value, message.payload)  # type: ignore
                    except (ValidationError, json.JSONDecodeError) as ve:
                        logger.warning(f"MQTT data validation error: {ve}")
                    except Exception as ex:
                        tb = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
                        logger.error(f"Error processing MQTT message:\n{tb}")

        except MqttError as conn_error:
            mqtt_state.is_running = False
            logger.warning(f"[MQTT] Connection error: %s | Reconnecting in {settings.MQTT_RECONNECT_TIMER}s…", str(conn_error))
            await asyncio.sleep(settings.MQTT_RECONNECT_TIMER)

        except asyncio.CancelledError:
            mqtt_state.is_running = False
            logger.info("MQTT listener cancelled during shutdown")
            raise

        except Exception as fatal:
            mqtt_state.is_running = False
            tb = "".join(traceback.format_exception(type(fatal), fatal, fatal.__traceback__))
            logger.critical("[MQTT] Fatal error in listener | restarting in %ss", settings.MQTT_RECONNECT_TIMER)
            await asyncio.sleep(settings.MQTT_RECONNECT_TIMER)
