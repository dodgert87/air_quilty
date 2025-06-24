from app.models.schemas.graphQL.sensor_meta_data_query import DateRange, SensorMetadataQuery
from app.models.schemas.graphQL.Sensor_data_query import SensorDataAdvancedQuery
from app.models.schemas.graphQL.inputs import SensorDataQueryInput, FieldRangeInput, SensorMetadataQueryInput
from app.utils.config import settings


def map_graphql_to_pydantic_sensor_data_query(
    gql_input: SensorDataQueryInput
) -> SensorDataAdvancedQuery:
    """
    Convert GraphQL sensor data query input into a validated Pydantic model.
    Includes range filter conversion, timestamp processing, and pagination bounds.
    """
    field_ranges_dict = {
        fr.field: [fr.min, fr.max] for fr in gql_input.range_filters or []
    }

    timestamps = None
    timestamp_start = None
    timestamp_end = None

    if gql_input.timestamp_filter:
        if gql_input.timestamp_filter.exact:
            timestamps = gql_input.timestamp_filter.timestamps
        elif gql_input.timestamp_filter.timestamps:
            sorted_ts = sorted(gql_input.timestamp_filter.timestamps)
            timestamp_start = sorted_ts[0]
            timestamp_end = sorted_ts[-1]

    return SensorDataAdvancedQuery(
        sensor_ids=gql_input.sensor_ids,
        timestamps=timestamps,
        timestamp_range_start=timestamp_start,
        timestamp_range_end=timestamp_end,
        field_ranges=field_ranges_dict,
        locations=gql_input.location_filter,
        models=gql_input.model_filter,
        is_active=gql_input.is_active,
        page=gql_input.page,
        page_size=min(gql_input.page_size or 10, settings.MAX_PAGE_SIZE)
    )


def map_graphql_to_pydantic_metadata_query(
    gql_input: SensorMetadataQueryInput
) -> SensorMetadataQuery:
    """
    Convert GraphQL sensor metadata input into validated Pydantic metadata query.
    Handles optional date range wrappers for creation and update timestamps.
    """
    return SensorMetadataQuery(
        sensor_ids=gql_input.sensor_ids,
        name_filter=gql_input.name_filter,
        locations=gql_input.location_filter, # type: ignore
        models=gql_input.model_filter, # type: ignore
        is_active=gql_input.is_active,
        created_at=DateRange(
            after=gql_input.created_at.after if gql_input.created_at else None,
            before=gql_input.created_at.before if gql_input.created_at else None,
        ),
        updated_at=DateRange(
            after=gql_input.updated_at.after if gql_input.updated_at else None,
            before=gql_input.updated_at.before if gql_input.updated_at else None,
        ),
    )
