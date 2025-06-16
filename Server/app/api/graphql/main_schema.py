import strawberry
from uuid import UUID

from app.utils.mappers import map_graphql_to_pydantic_metadata_query, map_graphql_to_pydantic_sensor_data_query
from app.models.schemas.graphQL.types import PaginatedSensorMetadata, Sensor, SensorData, PaginatedSensorData
from app.models.schemas.graphQL.inputs import SensorDataQueryInput, SensorMetadataQueryInput
from loguru import logger

# Import domain schemas
from app.models.schemas.rest.sensor_data_schemas import SensorDataOut

# Import domain logic
from app.domain.sensor_data_logic import query_sensor_data_advanced
from app.domain.sensor_logic import get_sensor_by_id, list_sensors, query_sensor_metadata_advanced
from app.models.schemas.rest.sensor_schemas import SensorOut


@strawberry.type
class Query:
    @strawberry.field
    async def sensor_data(self, filters: SensorDataQueryInput) -> PaginatedSensorData:
        """Unified sensor data query using multiple filters"""
        logger.info("[GraphQL] sensor_data called with filters=%s", filters)
        pyd_query = map_graphql_to_pydantic_sensor_data_query(filters)
        response = await query_sensor_data_advanced(pyd_query)
        logger.info("[GraphQL] sensor_data returned total=%d, items=%d", response.total, len(response.items))
        items = [SensorData(**item.model_dump()) for item in response.items]
        return PaginatedSensorData(
            items=items,
            total=response.total,
            page=response.page,
            page_size=response.page_size,
        )

    @strawberry.field
    async def sensor_metadata(self, filters: SensorMetadataQueryInput) -> PaginatedSensorMetadata:
        """Unified, paginated sensor metadata filter"""
        logger.info("[GraphQL] sensor_metadata (unified) called with filters=%s", filters)

        pyd_query = map_graphql_to_pydantic_metadata_query(filters)
        response = await query_sensor_metadata_advanced(pyd_query)

        items = [Sensor(**SensorOut.model_validate(s).model_dump()) for s in response.items]
        return PaginatedSensorMetadata(
            items=items,
            total=response.total,
            page=response.page,
            page_size=response.page_size,
        )


schema = strawberry.Schema(query=Query)