import json
from typing import Any, cast
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, patch, MagicMock

from app.constants.webhooks import WebhookEvent
from app.models.schemas.rest.sensor_schemas import SensorOut
from app.domain.mqtt_listener import (
    process_status_message,
    process_sensor_data,
    ensure_sensor_exists,
    handle_mqtt_message,
    mqtt_state
)
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn


@pytest.mark.asyncio
@patch("app.domain.mqtt_listener.safe_get_sensor_by_id", new_callable=AsyncMock)
@patch("app.domain.mqtt_listener.modify_sensor", new_callable=AsyncMock)
@patch("app.domain.mqtt_listener.dispatcher.dispatch", new_callable=AsyncMock)
async def test_process_status_message_valid_online(mock_dispatch, mock_modify, mock_get):
    sensor_id = uuid4()
    topic = f"A3/AirQuality/Connection/{sensor_id}"
    mock_get.return_value = MagicMock(is_active=False)

    mock_modify.return_value = SensorOut(
    sensor_id=sensor_id,
    name="Mock Sensor",
    location="Lab",
    model="GENERIC",
    is_active=True,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
    ).model_dump()

    await process_status_message(topic, "online")

    mock_dispatch.assert_any_await(WebhookEvent.SENSOR_STATUS_CHANGED, ANY)


@patch("app.domain.mqtt_listener.logger.warning")
@pytest.mark.asyncio
async def test_process_status_message_invalid_uuid(mock_warn):
    topic = "A3/AirQuality/Connection/invalid-uuid"
    await process_status_message(topic, "online")
    mock_warn.assert_called_once()
    assert "Invalid UUID" in mock_warn.call_args[0][0]

@pytest.mark.asyncio
@patch("app.domain.mqtt_listener.safe_get_sensor_by_id", new_callable=AsyncMock)
async def test_ensure_sensor_exists_false(mock_get):
    mock_get.return_value = None
    result = await ensure_sensor_exists(uuid4())
    assert result is False


@pytest.mark.asyncio
@patch("app.domain.mqtt_listener.safe_get_sensor_by_id", new_callable=AsyncMock)
async def test_ensure_sensor_exists_true(mock_get):
    mock_get.return_value = MagicMock(is_active=True)
    result = await ensure_sensor_exists(uuid4(), is_active=True)
    assert result is True

@pytest.mark.asyncio
@patch("app.domain.mqtt_listener.create_sensor", new_callable=AsyncMock)
@patch("app.domain.mqtt_listener.safe_get_sensor_by_id", new_callable=AsyncMock)
@patch("app.domain.mqtt_listener.create_sensor_data_entry", new_callable=AsyncMock)
@patch("app.domain.mqtt_listener.dispatcher.dispatch", new_callable=AsyncMock)
async def test_process_sensor_data_creates_sensor_and_dispatches(mock_dispatch, mock_create_data, mock_get, mock_create_sensor):
    sensor_id = uuid4()
    mock_get.return_value = None

    sensor_data = SensorDataIn(
        sensorid=sensor_id,
        timestamp=datetime.now(timezone.utc),
        temperature=23.5,
        humidity=50.0,
        pm1_0=1.0, pm2_5=2.0, pm10=3.0,
        tvoc=0.1, eco2=600, aqi=30.0,
        pmInAir1_0=10, pmInAir2_5=20, pmInAir10=30,
        particles0_3=1, particles0_5=2, particles1_0=3,
        particles2_5=4, particles5_0=5, particles10=6,
        compT=24.0, compRH=40.0, rawT=22.0, rawRH=38.0,
        rs0=100, rs1=200, rs2=300, rs3=400,
        co2=500,
    )

    mock_create_data.return_value = MagicMock(device_id=sensor_id)

    await process_sensor_data(sensor_data.model_dump_json(by_alias=True)) # type: ignore

    assert mqtt_state.is_running is True
    assert mqtt_state.last_device_id == sensor_id
    mock_dispatch.assert_any_await(WebhookEvent.SENSOR_DATA_RECEIVED, mock_create_data.return_value)
    mock_dispatch.assert_any_await(WebhookEvent.ALERT_TRIGGERED, mock_create_data.return_value)

@pytest.mark.asyncio
@patch("app.domain.mqtt_listener.process_status_message", new_callable=AsyncMock)
@patch("app.domain.mqtt_listener.process_sensor_data", new_callable=AsyncMock)
async def test_handle_mqtt_message_dispatches_correctly(mock_sensor_data, mock_status_message):
    await handle_mqtt_message("A3/AirQuality/Connection/abc", "online")
    mock_status_message.assert_awaited_once()

    await handle_mqtt_message("A3/AirQuality/Data", json.dumps({"sensorid": str(uuid4()), "timestamp": datetime.now().isoformat()}))
    mock_sensor_data.assert_awaited_once()


@patch("app.domain.mqtt_listener.logger.warning")
@pytest.mark.asyncio
async def test_handle_mqtt_message_unsupported_type(mock_warn):
    await handle_mqtt_message("some/topic", cast(Any, 12345))
    mock_warn.assert_called_once()
    assert "Unsupported MQTT payload type" in mock_warn.call_args[0][0]