import strawberry


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


@strawberry.type
class Query:
    """
    Root GraphQL query resolver.

    Contains:
    - sensor_data(): Resolves historical sensor readings based on multiple filters
    - sensor_metadata(): Resolves paginated sensor metadata records with filter support

    These resolvers map GraphQL inputs to internal Pydantic models and use
    domain logic to execute and paginate queries. Each route applies request-level
    rate limiting using `slowapi` and logs both execution and failures.
    """

    @strawberry.field
    async def sensor_data(
        self,
        filters: SensorDataQueryInput,
        info
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
            logger.info("[GraphQL] sensor_data called | filters=%s", filters)
            pyd_query = map_graphql_to_pydantic_sensor_data_query(filters)
            response = await query_sensor_data_advanced(pyd_query)

            logger.info("[GraphQL] sensor_data succeeded | total=%d, items=%d", response.total, len(response.items))
            items = [SensorData(**item.model_dump()) for item in response.items]

            return PaginatedSensorData(
                items=items,
                total=response.total,
                page=response.page,
                page_size=response.page_size,
            )

        except Exception as e:
            logger.exception("[GraphQL] sensor_data failed | filters=%s | error=%s", filters, str(e))
            from app.utils.exceptions_base import AppException
            raise AppException.from_internal_error("Sensor data query failed", domain="sensor")

    @strawberry.field
    async def sensor_metadata(
        self,
        filters: SensorMetadataQueryInput,
        info
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
            logger.info("[GraphQL] sensor_metadata called | filters=%s", filters)
            pyd_query = map_graphql_to_pydantic_metadata_query(filters)
            response = await query_sensor_metadata_advanced(pyd_query)

            items = [Sensor(**SensorOut.model_validate(s).model_dump()) for s in response.items]
            logger.info("[GraphQL] sensor_metadata succeeded | total=%d, items=%d", response.total, len(response.items))

            return PaginatedSensorMetadata(
                items=items,
                total=response.total,
                page=response.page,
                page_size=response.page_size,
            )

        except Exception as e:
            logger.exception("[GraphQL] sensor_metadata failed | filters=%s | error=%s", filters, str(e))
            from app.utils.exceptions_base import AppException
            raise AppException.from_internal_error("Sensor metadata query failed", domain="sensor")


# Final schema setup (exposed to ASGI app)
schema = strawberry.Schema(query=Query)
