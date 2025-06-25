from uuid import UUID
import pytest
from dateutil.parser import isoparse
from app.utils.config import settings
from app.utils.mappers import (
    map_graphql_to_pydantic_sensor_data_query,
    map_graphql_to_pydantic_metadata_query
)
from app.models.schemas.graphQL.inputs import (
    SensorDataQueryInput,
    FieldRangeInput,
    SensorMetadataQueryInput,
    TimestampFilterInput,
    DateRangeInput
)


def test_map_sensor_data_query_with_exact_timestamps():
    gql = SensorDataQueryInput(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")],
        timestamp_filter=TimestampFilterInput(
            timestamps=[isoparse("2025-06-01T12:00:00Z")],
            exact=True
        ),
        page=1,
        page_size=5
    )
    result = map_graphql_to_pydantic_sensor_data_query(gql)
    assert result.timestamps == [isoparse("2025-06-01T12:00:00Z")]
    assert result.timestamp_range_start is None


def test_map_sensor_data_query_with_range_timestamps():
    gql = SensorDataQueryInput(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")],
        timestamp_filter=TimestampFilterInput(
            timestamps=[
                isoparse("2025-06-01T12:00:00Z"),
                isoparse("2025-06-02T12:00:00Z")
            ],
            exact=False
        ),
        page=1
    )
    result = map_graphql_to_pydantic_sensor_data_query(gql)
    assert result.timestamp_range_start == isoparse("2025-06-01T12:00:00Z")
    assert result.timestamp_range_end == isoparse("2025-06-02T12:00:00Z")
    assert result.timestamps is None


def test_map_sensor_data_query_with_field_ranges():
    gql = SensorDataQueryInput(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")],
        range_filters=[FieldRangeInput(field="temperature", min=20, max=30)],
        page=2
    )
    result = map_graphql_to_pydantic_sensor_data_query(gql)
    assert result.field_ranges is not None
    assert result.field_ranges["temperature"] == [20, 30]


def test_map_sensor_data_query_applies_max_page_size_limit():
    gql = SensorDataQueryInput(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")],
        page=1,
        page_size=settings.MAX_PAGE_SIZE + 100
    )
    result = map_graphql_to_pydantic_sensor_data_query(gql)
    assert result.page_size == settings.MAX_PAGE_SIZE


def test_map_sensor_data_query_with_null_fields_defaults_correctly():
    gql = SensorDataQueryInput(sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")])
    result = map_graphql_to_pydantic_sensor_data_query(gql)
    assert result.page_size <= settings.MAX_PAGE_SIZE


def test_map_metadata_query_with_full_filters():
    gql = SensorMetadataQueryInput(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")],
        name_filter=["CO2"],
        location_filter=["Lab"],
        model_filter=["M-100"],
        is_active=True,
        created_at=DateRangeInput(after=isoparse("2025-01-01T00:00:00Z"), before=isoparse("2025-06-01T00:00:00Z")),
        updated_at=DateRangeInput(after=isoparse("2025-03-01T00:00:00Z"), before=isoparse("2025-06-01T00:00:00Z"))
    )
    result = map_graphql_to_pydantic_metadata_query(gql)
    assert result.created_at is not None
    assert result.created_at.after == isoparse("2025-01-01T00:00:00Z")
    assert result.updated_at is not None
    assert result.updated_at.before == isoparse("2025-06-01T00:00:00Z")


def test_map_metadata_query_with_null_date_ranges():
    gql = SensorMetadataQueryInput(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")]
    )
    result = map_graphql_to_pydantic_metadata_query(gql)
    assert result.created_at is not None
    assert result.created_at.after is None
    assert result.updated_at is not None
    assert result.updated_at.before is None


def test_map_metadata_query_partial_created_updated_dates():
    gql = SensorMetadataQueryInput(
        sensor_ids=[UUID("00000000-0000-0000-0000-000000000001")],
        created_at=DateRangeInput(after=isoparse("2025-01-01T00:00:00Z")),
        updated_at=DateRangeInput(before=isoparse("2025-06-01T00:00:00Z"))
    )
    result = map_graphql_to_pydantic_metadata_query(gql)
    assert result.created_at is not None
    assert result.created_at.after == isoparse("2025-01-01T00:00:00Z")
    assert result.updated_at is not None
    assert result.updated_at.before == isoparse("2025-06-01T00:00:00Z")
