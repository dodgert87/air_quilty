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

    @strawberry.field
    async def sensor_data(
        self,
        filters: SensorDataQueryInput,
        info
    ) -> PaginatedSensorData:
        request = info.context["request"]
        await limiter.limit(settings.GRAPHQL_DATA_QUERY_LIMIT)(request)

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
        request = info.context["request"]
        await limiter.limit(settings.GRAPHQL_META_QUERY_LIMIT)(request)

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



# Final schema setup
schema = strawberry.Schema(query=Query)
