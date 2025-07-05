import strawberry


from app.utils.exceptions_base import AppException
from app.utils.mappers import (
    map_graphql_to_pydantic_metadata_query,
    map_graphql_to_pydantic_sensor_data_query
)
from app.models.schemas.graphQL.types import (
    PaginatedSensorMetadata, Sensor, SensorData, PaginatedSensorData
)
from app.models.schemas.graphQL.inputs import (
    SensorDataQueryInput, SensorMetadataQueryInput
)
from loguru import logger
from app.utils.config import settings
from app.middleware.rate_limit_middleware import limiter

# Import domain logic
from app.domain.sensor_data_logic import query_sensor_data_advanced
from app.domain.sensor_logic import (
    query_sensor_metadata_advanced
)
from app.models.schemas.rest.sensor_schemas import SensorOut



# ------------------------------------------------------------------ sensor data
@strawberry.type
class QuerySensorData:
    @strawberry.field(name="sensorData")
    async def sensor_data(
        self, filters: SensorDataQueryInput, info
    ) -> PaginatedSensorData:

        """
        Resolve sensorData GraphQL query.

        Filters supported:
        - sensor_ids: List of sensor UUIDs
        - location/model/is_active: Metadata filters
        - timestamp_filter: Exact or range-based time query
        - range_filters: Per-field [min, max] numeric filters
        - Pagination: page and page_size

        Flow:
        - Rate limit the request using GRAPHQL_DATA_QUERY_LIMIT
        - Convert GraphQL input to SensorDataAdvancedQuery
        - Execute domain-level advanced query
        - Return paginated result with GraphQL SensorData type

        Returns:
            PaginatedSensorData (GraphQL type) with list of SensorData items
        """

        try:
            logger.info("[GraphQL] sensor_data | %s", filters)
            pyd_query = map_graphql_to_pydantic_sensor_data_query(filters)
            resp = await query_sensor_data_advanced(pyd_query)
            items = [SensorData(**i.model_dump()) for i in resp.items]
            return PaginatedSensorData(
                items=items,
                total=resp.total,
                page=resp.page,
                page_size=resp.page_size,
            )
        except Exception as e:
            logger.exception("[GraphQL] sensor_data failed | %s", e)
            raise AppException.from_internal_error(
                "Sensor data query failed", domain="sensor"
            )


# ------------------------------------------------------------------ metadata
@strawberry.type
class QuerySensorMeta:
    @strawberry.field(name="sensorMetadata")
    async def sensor_metadata(
        self, filters: SensorMetadataQueryInput, info
    ) -> PaginatedSensorMetadata:

        """
        Resolve sensorMetadata GraphQL query.

        Filters supported:
        - sensor_ids, name_filter, location_filter, model_filter, is_active
        - created_at, updated_at: range filters
        - Pagination: page and page_size

        Flow:
        - Apply GRAPHQL_META_QUERY_LIMIT rate limit
        - Convert GraphQL input to SensorMetadataQuery (Pydantic)
        - Call domain-level query and paginate results
        - Return GraphQL-formatted metadata entries

        Returns:
            PaginatedSensorMetadata (GraphQL type) with Sensor entries
        """
        try:
            logger.info("[GraphQL] sensor_metadata | %s", filters)
            pyd_query = map_graphql_to_pydantic_metadata_query(filters)
            resp = await query_sensor_metadata_advanced(pyd_query)
            items = [
                Sensor(**SensorOut.model_validate(s).model_dump())
                for s in resp.items
            ]
            return PaginatedSensorMetadata(
                items=items,
                total=resp.total,
                page=resp.page,
                page_size=resp.page_size,
            )
        except Exception as e:
            logger.exception("[GraphQL] sensor_metadata failed | %s", e)
            raise AppException.from_internal_error(
                "Sensor metadata query failed", domain="sensor"
            )


sensor_data_schema = strawberry.Schema(query=QuerySensorData)
sensor_meta_schema = strawberry.Schema(query=QuerySensorMeta)