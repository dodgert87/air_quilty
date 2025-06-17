import asyncio
from datetime import datetime, timezone
import json
import traceback
from typing import Any, Optional
from uuid import UUID

from aiomqtt import Client, MqttError
from loguru import logger
from pydantic import ValidationError

from app.domain.sensor_logic import create_sensor, get_sensor_by_id, safe_get_sensor_by_id
from app.models.schemas.rest.sensor_schemas import SensorCreate
from app.utils.config import settings
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn
from app.domain.sensor_data_logic import create_sensor_data_entry
from app.models.DB_tables.rest_logs import LogDomain
from app.utils.logger_utils import log_background_task_error

class MQTTListenerState:
    is_running: bool = False
    last_message_at: Optional[datetime] = None
    last_device_id: Optional[UUID] = None
    message_count: int = 0

mqtt_state = MQTTListenerState()
async def listen_to_mqtt() -> None:
    """
    Background task that keeps a persistent connection to the MQTT broker,
    auto-reconnects on failure, validates each JSON payload, and persists it
    through the existing domain service.
    """
    logger.info("Starting MQTT listener with auto-reconnect…")

    while True:
        try:
            # ───────────────────── Connect (auto-closed with context) ──────────────────
            async with Client(
                hostname=settings.MQTT_BROKER,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USERNAME,
                password=settings.MQTT_PASSWORD,
            ) as client:

                await client.subscribe(settings.MQTT_TOPIC, qos=settings.MQTT_QOS)
                logger.info(f"Subscribed to topic: {settings.MQTT_TOPIC}")

                # ─────────────── Consume messages (aiomqtt async iterator) ─────────────
                async for message in client.messages:
                    try:
                        raw: Any = message.payload  # could be bytes, str, etc.

                        # ─── Safe decode ───────────────────────────────────────────────
                        if isinstance(raw, (bytes, bytearray)):
                            text = raw.decode()
                        elif isinstance(raw, memoryview):
                            text = raw.tobytes().decode()
                        elif isinstance(raw, str):
                            text = raw
                        else:
                            logger.warning(
                                f"Unsupported MQTT payload type {type(raw)}; skipping"
                            )
                            continue
                        # ----------------------------------------------------------------

                        payload_dict = json.loads(text)
                        logger.debug(f"MQTT payload parsed: {payload_dict}")

                        data = SensorDataIn(**payload_dict)

                        # Check if the sensor exists, else create a placeholder
                        if not await safe_get_sensor_by_id(data.device_id):
                            placeholder = SensorCreate(
                                sensor_id=data.device_id,
                                name="UNKNOWN",
                                location="PENDING",
                                model="GENERIC",
                                is_active=True
                            )
                            await create_sensor(placeholder)
                            logger.info(f"Created placeholder sensor for device {data.device_id}")


                        await create_sensor_data_entry(data)
                        #logger.info(f"Sensor data stored from {data.device_id}")
                        mqtt_state.is_running = True
                        mqtt_state.last_message_at = datetime.now(timezone.utc)
                        mqtt_state.last_device_id = data.device_id
                        mqtt_state.message_count += 1

                    except (ValidationError, json.JSONDecodeError) as ve:
                        logger.warning(f"MQTT data validation error: {ve}")

                    except Exception as ex:
                        tb = "".join(
                            traceback.format_exception(type(ex), ex, ex.__traceback__)
                        )
                        logger.error(f"Error processing MQTT message:\n{tb}")
                        await log_background_task_error(
                            domain=LogDomain.SENSOR,
                            error_message=tb,
                            context_label="MQTT_MESSAGE",
                        )

        # ─────────────────────── Connection-level failures ──────────────────────────
        except MqttError as conn_error:
            mqtt_state.is_running = False
            tb = "".join(
                traceback.format_exception(
                    type(conn_error), conn_error, conn_error.__traceback__
                )
            )
            await log_background_task_error(
                domain=LogDomain.SENSOR,
                error_message=tb,
                context_label="MQTT_RECONNECT",
            )
            await asyncio.sleep(5)  # simple back-off before retry

        # ───────────────────────── Graceful shutdown ────────────────────────────────
        except asyncio.CancelledError:
            mqtt_state.is_running = False
            logger.info("MQTT listener cancelled during shutdown")
            raise

        # ───────────────────── Any other fatal, unexpected error ────────────────────
        except Exception as fatal:
            mqtt_state.is_running = False
            tb = "".join(
                traceback.format_exception(type(fatal), fatal, fatal.__traceback__)
            )
            await log_background_task_error(
                domain=LogDomain.SENSOR,
                error_message=tb,
                context_label="MQTT_FATAL",
            )
            await asyncio.sleep(settings.MQTT_RECONNECT_TIMER)  # longer back-off before re-entering loop
