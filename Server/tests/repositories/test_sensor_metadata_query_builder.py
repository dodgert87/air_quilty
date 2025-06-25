from uuid import UUID
from dateutil.parser import isoparse
import pytest
from sqlalchemy.dialects import postgresql

from app.infrastructure.database.repository.graphQL.sensor_metadata_graphql_repository import sensor_metadata_graphql_repository
from app.models.schemas.graphQL.sensor_meta_data_query import SensorMetadataQuery, DateRange


def compile_query_to_sql(query) -> str:
    return str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


@pytest.mark.asyncio
async def test_query_with_sensor_ids():
    payload = SensorMetadataQuery(sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")])
    stmt = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    sql = compile_query_to_sql(stmt)
    assert "sensors.sensor_id IN" in sql


@pytest.mark.asyncio
async def test_query_with_name_filter():
    payload = SensorMetadataQuery(name_filter=["CO2 Sensor"])
    stmt = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    sql = compile_query_to_sql(stmt)
    assert "sensors.name IN" in sql


@pytest.mark.asyncio
async def test_query_with_location_filter():
    payload = SensorMetadataQuery(location_filter=["Lab A"])
    stmt = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    sql = compile_query_to_sql(stmt)
    assert "sensors.location IN" in sql


@pytest.mark.asyncio
async def test_query_with_model_filter():
    payload = SensorMetadataQuery(model_filter=["Model-X"])
    stmt = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    sql = compile_query_to_sql(stmt)
    assert "sensors.model IN" in sql


@pytest.mark.asyncio
async def test_query_with_is_active_filter():
    payload = SensorMetadataQuery(is_active=True)
    stmt = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    sql = compile_query_to_sql(stmt)
    assert "sensors.is_active = true" in sql


@pytest.mark.asyncio
async def test_query_with_created_at_range():
    payload = SensorMetadataQuery(
        created_at=DateRange(
            after=isoparse("2025-01-01T00:00:00Z"),
            before=isoparse("2025-06-01T00:00:00Z")
        )
    )
    stmt = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    sql = compile_query_to_sql(stmt)
    assert "sensors.created_at >=" in sql
    assert "sensors.created_at <=" in sql


@pytest.mark.asyncio
async def test_query_with_updated_at_range():
    payload = SensorMetadataQuery(
        updated_at=DateRange(
            after=isoparse("2025-03-01T00:00:00Z"),
            before=isoparse("2025-06-01T00:00:00Z")
        )
    )
    stmt = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    sql = compile_query_to_sql(stmt)
    assert "sensors.updated_at >=" in sql
    assert "sensors.updated_at <=" in sql


@pytest.mark.asyncio
async def test_query_with_all_filters_combined():
    payload = SensorMetadataQuery(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")],
        name_filter=["CO2"],
        location_filter=["Room 1"],
        model_filter=["MX-1"],
        is_active=False,
        created_at=DateRange(after=isoparse("2024-01-01T00:00:00Z")),
        updated_at=DateRange(before=isoparse("2025-12-31T00:00:00Z"))
    )
    stmt = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    sql = compile_query_to_sql(stmt)

    assert "sensors.sensor_id IN" in sql
    assert "sensors.name IN" in sql
    assert "sensors.location IN" in sql
    assert "sensors.model IN" in sql
    assert "sensors.is_active = false" in sql
    assert "sensors.created_at >=" in sql
    assert "sensors.updated_at <=" in sql
