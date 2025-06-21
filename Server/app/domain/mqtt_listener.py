import asyncio
from datetime import datetime, timezone
import json
import traceback
from uuid import UUID

from aiomqtt import Client, MqttError
from loguru import logger
from pydantic import ValidationError

from app.infrastructure.database.repository.restAPI.sensor_repository import modify_sensor
from app.domain.webhooks.dispatcher import dispatcher
from app.constants.webhooks import WebhookEvent
from app.domain.sensor_logic import create_sensor, get_sensor_by_id, safe_get_sensor_by_id
from app.models.schemas.rest.sensor_schemas import SensorCreate, SensorOut, SensorUpdate
from app.utils.config import settings
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn, SensorDataOut
from app.domain.sensor_data_logic import create_sensor_data_entry
from app.models.DB_tables.rest_logs import LogDomain
from app.utils.logger_utils import log_background_task_error

class MQTTListenerState:
    is_running: bool = False
    last_message_at: datetime | None = None
    last_device_id: UUID | None = None
    message_count: int = 0


mqtt_state = MQTTListenerState()


async def listen_to_mqtt() -> None:
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
                        raw = message.payload
                        if isinstance(raw, (bytes, bytearray)):
                            text = raw.decode()
                        elif isinstance(raw, memoryview):
                            text = raw.tobytes().decode()
                        elif isinstance(raw, str):
                            text = raw
                        else:
                            logger.warning(f"Unsupported MQTT payload type {type(raw)}; skipping")
                            continue

                        topic = message.topic.value

                        # ───── Sensor Status Message ─────
                        if topic.startswith("A3/AirQuality/Connection/"):
                            sensor_id_str = topic.split("/")[-1]
                            try:
                                sensor_id = UUID(sensor_id_str)
                            except ValueError:
                                logger.warning(f"Invalid UUID in connection topic: {sensor_id_str}")
                                continue

                            is_active = text.strip().lower() == "online"
                            await ensure_sensor_exists(sensor_id, is_active=is_active)

                            update_data = SensorUpdate(is_active=is_active)
                            sensor = await modify_sensor(sensor_id, update_data)
                            if sensor:
                                sensor_out = SensorOut.model_validate(sensor)
                                #await dispatcher.dispatch(WebhookEvent.SENSOR_STATUS_CHANGED, sensor_out)
                                logger.info(f"Updated sensor {sensor_id} status to {'active' if is_active else 'inactive'} via MQTT")
                            continue

                        # ───── Sensor Data Message ─────
                        payload_dict = json.loads(text)
                        logger.debug(f"MQTT payload parsed: {payload_dict}")
                        data = SensorDataIn(**payload_dict)

                        await ensure_sensor_exists(data.device_id)

                        stored: SensorDataOut = await create_sensor_data_entry(data)
                        #await dispatcher.dispatch(WebhookEvent.SENSOR_DATA_RECEIVED, stored)
                        await dispatcher.dispatch(WebhookEvent.ALERT_TRIGGERED, stored)

                        mqtt_state.is_running = True
                        mqtt_state.last_message_at = datetime.now(timezone.utc)
                        mqtt_state.last_device_id = data.device_id
                        mqtt_state.message_count += 1

                    except (ValidationError, json.JSONDecodeError) as ve:
                        logger.warning(f"MQTT data validation error: {ve}")

                    except Exception as ex:
                        tb = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
                        logger.error(f"Error processing MQTT message:\n{tb}")
                        await log_background_task_error(
                            domain=LogDomain.SENSOR,
                            error_message=tb,
                            context_label="MQTT_MESSAGE",
                        )

        except MqttError as conn_error:
            mqtt_state.is_running = False
            tb = "".join(traceback.format_exception(type(conn_error), conn_error, conn_error.__traceback__))
            await log_background_task_error(
                domain=LogDomain.SENSOR,
                error_message=tb,
                context_label="MQTT_RECONNECT",
            )
            await asyncio.sleep(5)

        except asyncio.CancelledError:
            mqtt_state.is_running = False
            logger.info("MQTT listener cancelled during shutdown")
            raise

        except Exception as fatal:
            mqtt_state.is_running = False
            tb = "".join(traceback.format_exception(type(fatal), fatal, fatal.__traceback__))
            await log_background_task_error(
                domain=LogDomain.SENSOR,
                error_message=tb,
                context_label="MQTT_FATAL",
            )
            await asyncio.sleep(settings.MQTT_RECONNECT_TIMER)



async def ensure_sensor_exists(sensor_id: UUID, is_active: bool = True) -> None:
    if not await safe_get_sensor_by_id(sensor_id):
        placeholder = SensorCreate(
            sensor_id=sensor_id,
            name="UNKNOWN",
            location="PENDING",
            model="GENERIC",
            is_active=is_active
        )
        await create_sensor(placeholder)
        logger.info(f"Created placeholder sensor for device {sensor_id}")