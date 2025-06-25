from uuid import UUID
from dateutil.parser import isoparse
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.selectable import Select

from app.infrastructure.database.repository.graphQL.sensor_data_graphql_repository import build_sensor_data_query
from app.models.schemas.graphQL.Sensor_data_query import SensorDataAdvancedQuery


def compile_query_to_sql(query: Select) -> str:
    return str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


@pytest.mark.asyncio
async def test_query_with_only_sensor_ids():
    payload = SensorDataAdvancedQuery(sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")])
    query = await build_sensor_data_query(payload)
    sql = compile_query_to_sql(query)
    assert "WHERE sensor_data.device_id IN" in sql


@pytest.mark.asyncio
async def test_query_with_exact_timestamps():
    payload = SensorDataAdvancedQuery(
        timestamps=[isoparse("2025-06-01T00:00:00Z"), isoparse("2025-06-02T00:00:00Z")]
    )
    query = await build_sensor_data_query(payload)
    sql = compile_query_to_sql(query)
    assert "sensor_data.timestamp IN" in sql


@pytest.mark.asyncio
async def test_query_with_timestamp_range():
    payload = SensorDataAdvancedQuery(
        timestamp_range_start=isoparse("2025-06-01T00:00:00Z"),
        timestamp_range_end=isoparse("2025-06-02T00:00:00Z")
    )
    query = await build_sensor_data_query(payload)
    sql = compile_query_to_sql(query)
    assert "sensor_data.timestamp >= " in sql
    assert "sensor_data.timestamp <= " in sql


@pytest.mark.asyncio
async def test_query_with_field_range():
    payload = SensorDataAdvancedQuery(
        field_ranges={"pm2_5": [10.0, 50.0]}
    )
    query = await build_sensor_data_query(payload)
    sql = compile_query_to_sql(query)
    assert "sensor_data.pm2_5 >= 10.0" in sql
    assert "sensor_data.pm2_5 <= 50.0" in sql


@pytest.mark.asyncio
async def test_query_with_metadata_filters_triggers_join():
    payload = SensorDataAdvancedQuery(
        locations=["Lab A"],
        models=["M-100"],
        is_active=True
    )
    query = await build_sensor_data_query(payload)
    sql = compile_query_to_sql(query)
    assert "JOIN sensors ON sensors.sensor_id = sensor_data.device_id" in sql
    assert "sensors.location IN" in sql
    assert "sensors.model IN" in sql
    assert "sensors.is_active = true" in sql


@pytest.mark.asyncio
async def test_query_without_metadata_does_not_join():
    payload = SensorDataAdvancedQuery(
        field_ranges={"pm10": [None, 25.0]}
    )
    query = await build_sensor_data_query(payload)
    sql = compile_query_to_sql(query)
    assert "JOIN sensor" not in sql


@pytest.mark.asyncio
async def test_query_combines_all_filters():
    payload = SensorDataAdvancedQuery(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")],
        timestamps=[isoparse("2025-06-01T00:00:00Z")],
        field_ranges={"temperature": [15.0, 25.0]},
        locations=["Lab A"],
        models=["Model-X"],
        is_active=False
    )
    query = await build_sensor_data_query(payload)
    sql = compile_query_to_sql(query)

    assert "sensor_data.device_id IN" in sql
    assert "sensor_data.timestamp IN" in sql
    assert "sensor_data.temperature >= 15.0" in sql
    assert "sensor_data.temperature <= 25.0" in sql

    assert "JOIN sensors ON sensors.sensor_id = sensor_data.device_id" in sql
    assert "sensors.location IN" in sql
    assert "sensors.model IN" in sql
    assert "sensors.is_active = false" in sql