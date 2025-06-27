import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from app.utils.config import settings

from app.domain import sensor_data_logic
from app.models.schemas.rest.sensor_data_schemas import (
    SensorDataIn, SensorDataOut, SensorDataPartialOut,
    SensorRangeQuery, SensorQuery, SensorTimestampQuery
)
from app.utils.exceptions_base import AppException
from app.models.schemas.graphQL.Sensor_data_query import SensorDataAdvancedQuery


@pytest.mark.asyncio
@patch("app.domain.sensor_data_logic.sensor_data_repository.search_by_attribute_ranges", new_callable=AsyncMock)
@patch("app.domain.sensor_data_logic.paginate_query", new_callable=AsyncMock)
async def test_query_sensor_data_by_ranges(mock_paginate, mock_search):
    payload = SensorRangeQuery(ranges={"pm2_5": [None, 50]}, page=1)
    mock_search.return_value = ["fake_query"]
    mock_paginate.return_value = ["paginated"]

    result = await sensor_data_logic.query_sensor_data_by_ranges(payload)

    mock_search.assert_awaited_once_with(payload)
    mock_paginate.assert_awaited_once_with(["fake_query"], page=1, schema=SensorDataPartialOut, page_size=settings.DEFAULT_PAGE_SIZE)
    assert result == ["paginated"]


@pytest.mark.asyncio
@patch("app.domain.sensor_data_logic.sensor_data_repository.insert_sensor_data", new_callable=AsyncMock)
async def test_create_sensor_data_entry(mock_insert):
    sensor_id = uuid4()
    payload = SensorDataIn(
        sensorid=sensor_id,
        timestamp=datetime.now(timezone.utc),
        temperature=23.5,
        humidity=40.0,
        pm1_0=1, pm2_5=2, pm10=3,
        tvoc=0.1, eco2=500, aqi=30.0,
        pmInAir1_0=5, pmInAir2_5=10, pmInAir10=15,
        particles0_3=100, particles0_5=50, particles1_0=30,
        particles2_5=25, particles5_0=20, particles10=10,
        compT=23.0, compRH=50.0, rawT=22.5, rawRH=48.0,
        rs0=100, rs1=200, rs2=300, rs3=400,
        co2=420
    )
    mock_insert.return_value = {
        **payload.model_dump(),
        "id": uuid4()
    }
    result = await sensor_data_logic.create_sensor_data_entry(payload)
    assert isinstance(result, SensorDataOut)
    assert result.device_id == sensor_id


@pytest.mark.asyncio
@patch("app.domain.sensor_data_logic.sensor_data_repository.fetch_latest_by_sensor", new_callable=AsyncMock)
@patch("app.domain.sensor_data_logic.sensor_repository.fetch_sensor_by_id", new_callable=AsyncMock)
async def test_get_latest_entries_for_sensors_valid(mock_get_sensor, mock_latest):
    sid = uuid4()
    mock_get_sensor.return_value = MagicMock(sensor_id=sid)
    mock_latest.return_value = {"device_id": sid}
    result = await sensor_data_logic.get_latest_entries_for_sensors([sid])
    assert result == [{"device_id": sid}]
    mock_latest.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.domain.sensor_data_logic.sensor_repository.fetch_all_sensors", new_callable=AsyncMock)
@patch("app.domain.sensor_data_logic.sensor_data_repository.fetch_latest_by_sensor", new_callable=AsyncMock)
@patch("app.domain.sensor_data_logic.sensor_repository.fetch_sensor_by_id", new_callable=AsyncMock)
async def test_get_latest_entries_for_sensors_none_passed(mock_get, mock_latest, mock_all):
    sid = uuid4()
    mock_all.return_value = [MagicMock(sensor_id=sid)]
    mock_get.return_value = MagicMock()
    mock_latest.return_value = {"device_id": sid}
    result = await sensor_data_logic.get_latest_entries_for_sensors(None)
    assert len(result) == 1


@pytest.mark.asyncio
@patch("app.domain.sensor_data_logic.sensor_data_repository.search_by_timestamps", new_callable=AsyncMock)
@patch("app.domain.sensor_data_logic.paginate_query", new_callable=AsyncMock)
async def test_query_sensor_data_by_timestamps(mock_paginate, mock_search):
    payload = SensorTimestampQuery(timestamps=[datetime.now(timezone.utc)], exact=True, page=2)
    mock_search.return_value = ["query"]
    mock_paginate.return_value = ["result"]
    result = await sensor_data_logic.query_sensor_data_by_timestamps(payload)
    assert result == ["result"]


@pytest.mark.asyncio
@patch("app.domain.sensor_data_logic.sensor_data_repository.search_by_sensor_id", new_callable=AsyncMock)
@patch("app.domain.sensor_data_logic.sensor_repository.fetch_sensor_by_id", new_callable=AsyncMock)
@patch("app.domain.sensor_data_logic.paginate_query", new_callable=AsyncMock)
async def test_get_all_data_by_sensor_success(mock_paginate, mock_get_sensor, mock_search):
    sid = uuid4()
    payload = SensorQuery(sensor_id=sid, page=1)
    mock_get_sensor.return_value = MagicMock()
    mock_search.return_value = ["q"]
    mock_paginate.return_value = ["data"]
    result = await sensor_data_logic.get_all_data_by_sensor(payload)
    assert result == ["data"]


@pytest.mark.asyncio
@patch("app.domain.sensor_data_logic.sensor_repository.fetch_sensor_by_id", new_callable=AsyncMock)
async def test_get_all_data_by_sensor_not_found(mock_get_sensor):
    sid = uuid4()
    payload = SensorQuery(sensor_id=sid, page=1)
    mock_get_sensor.return_value = None
    with pytest.raises(AppException) as e:
        await sensor_data_logic.get_all_data_by_sensor(payload)
    assert e.value.status_code == 404
    assert "Sensor ID" in e.value.message


@pytest.mark.asyncio
@patch("app.domain.sensor_data_logic.sensor_data_graphql_repository.build_sensor_data_query", new_callable=AsyncMock)
@patch("app.domain.sensor_data_logic.paginate_query", new_callable=AsyncMock)
async def test_query_sensor_data_advanced(mock_paginate, mock_build):
    payload = SensorDataAdvancedQuery(
        sensor_ids=[],
        timestamps=None,
        timestamp_range_start=None,
        timestamp_range_end=None,
        field_ranges={"pm2_5": [None, 25.0]},
        locations=None,
        models=None,
        is_active=None,
        page=1,
        page_size=settings.DEFAULT_PAGE_SIZE
    )

    mock_build.return_value = ["query"]
    mock_paginate.return_value = ["paginated"]  # ✅ ensure return value is defined

    result = await sensor_data_logic.query_sensor_data_advanced(payload)

    mock_paginate.assert_awaited_once_with(
        ["query"],
        page=1,
        schema=SensorDataOut,
        page_size=settings.DEFAULT_PAGE_SIZE
    )

    assert result == ["paginated"]
