import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.domain import sensor_logic
from app.models.schemas.rest.sensor_schemas import SensorCreate, SensorUpdate, SensorOut
from app.models.schemas.webhook.sensor_created import SensorCreatedPayload
from app.models.schemas.webhook.webhook_schema import SensorDeletedPayload
from app.models.schemas.graphQL.sensor_meta_data_query import SensorMetadataQuery
from app.constants.webhooks import WebhookEvent
from app.utils.exceptions_base import SensorNotFoundError
from app.utils.config import settings


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.sensor_repository.insert_sensor", new_callable=AsyncMock)
@patch("app.domain.sensor_logic.dispatcher.dispatch", new_callable=AsyncMock)
async def test_create_sensor_dispatches_webhook(mock_dispatch, mock_insert):
    sensor_id = uuid4()
    fake_sensor = SensorOut(
        sensor_id=sensor_id,
        name="TestSensor",
        location="Lab",
        model="GENERIC",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    mock_insert.return_value = fake_sensor

    payload = SensorCreate(
        sensor_id=sensor_id,
        name="TestSensor",
        location="Lab",
        model="GENERIC",
        is_active=True
    )

    result = await sensor_logic.create_sensor(payload)

    assert result == fake_sensor
    mock_dispatch.assert_awaited_once()
    event, dispatched_payload = mock_dispatch.await_args.args
    assert event == WebhookEvent.SENSOR_CREATED
    assert isinstance(dispatched_payload, SensorCreatedPayload)
    assert dispatched_payload.sensor_id == sensor_id


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.sensor_repository.fetch_sensor_by_id", new_callable=AsyncMock)
async def test_get_sensor_by_id_found(mock_fetch):
    sensor_id = uuid4()
    mock_fetch.return_value = MagicMock()
    result = await sensor_logic.get_sensor_by_id(sensor_id)
    assert result == mock_fetch.return_value


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.sensor_repository.fetch_sensor_by_id", new_callable=AsyncMock)
async def test_get_sensor_by_id_not_found_raises(mock_fetch):
    sensor_id = uuid4()
    mock_fetch.return_value = None
    with pytest.raises(SensorNotFoundError):
        await sensor_logic.get_sensor_by_id(sensor_id)


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.get_sensor_by_id", new_callable=AsyncMock)
async def test_safe_get_sensor_by_id_found(mock_get):
    sid = uuid4()
    mock_get.return_value = MagicMock()
    result = await sensor_logic.safe_get_sensor_by_id(sid)
    assert result == mock_get.return_value


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.get_sensor_by_id", new_callable=AsyncMock)
async def test_safe_get_sensor_by_id_not_found(mock_get):
    mock_get.side_effect = SensorNotFoundError(uuid4())
    result = await sensor_logic.safe_get_sensor_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.sensor_repository.fetch_all_sensors", new_callable=AsyncMock)
async def test_list_sensors(mock_fetch):
    mock_fetch.return_value = [MagicMock()]
    result = await sensor_logic.list_sensors()
    assert result == mock_fetch.return_value


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.sensor_repository.modify_sensor", new_callable=AsyncMock)
@patch("app.domain.sensor_logic.dispatcher.dispatch", new_callable=AsyncMock)
async def test_update_sensor_success(mock_dispatch, mock_modify):
    sid = uuid4()
    mock_sensor = SensorOut(
        sensor_id=sid,
        name="Updated",
        location="Room A",
        model="GENERIC",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    mock_modify.return_value = mock_sensor.model_dump()

    result = await sensor_logic.update_sensor(sid, SensorUpdate(is_active=True))
    assert isinstance(result, SensorOut)
    mock_dispatch.assert_awaited_once_with(WebhookEvent.SENSOR_STATUS_CHANGED, result)


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.sensor_repository.modify_sensor", new_callable=AsyncMock)
async def test_update_sensor_not_found(mock_modify):
    mock_modify.return_value = None
    with pytest.raises(SensorNotFoundError):
        await sensor_logic.update_sensor(uuid4(), SensorUpdate(is_active=True))


@pytest.mark.asyncio
@patch("app.domain.sensor_logic.sensor_repository.remove_sensor", new_callable=AsyncMock)
@patch("app.domain.sensor_logic.dispatcher.dispatch", new_callable=AsyncMock)
async def test_delete_sensor_success(mock_dispatch, mock_remove):
    sid = uuid4()
    mock_remove.return_value = True
    result = await sensor_logic.delete_sensor(sid)
    assert result is True
    args = mock_dispatch.await_args.args
    assert args[0] == WebhookEvent.SENSOR_DELETED
