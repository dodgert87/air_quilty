from datetime import datetime, timezone
from uuid import UUID
from loguru import logger

from app.models.schemas.webhook.webhook_schema import SensorDeletedPayload, SensorCreatedPayload
from app.constants.webhooks import WebhookEvent
from app.domain.pagination import paginate_query
from app.infrastructure.database.repository.graphQL.sensor_metadata_graphql_repository import sensor_metadata_graphql_repository
from app.models.schemas.graphQL.sensor_meta_data_query import SensorMetadataQuery
from app.models.DB_tables.sensor import Sensor
from app.models.schemas.rest.sensor_schemas import SensorCreate, SensorOut, SensorUpdate
from app.infrastructure.database.repository.restAPI import sensor_repository
from app.utils.exceptions_base import SensorNotFoundError
from app.utils.config import settings
from app.domain.webhooks.dispatcher import dispatcher

async def create_sensor(sensor_data: SensorCreate):
    """
    Create a new sensor in the database and dispatch a SENSOR_CREATED webhook.

    Args:
        sensor_data: Pydantic model containing sensor info.

    Returns:
        Sensor: The created SQLAlchemy ORM model instance.
    """
    sensor = await sensor_repository.insert_sensor(sensor_data)
    logger.info(f"Sensor created with ID={sensor.sensor_id}")

    payload = SensorCreatedPayload(
        sensor_id=sensor.sensor_id,
        name=sensor.name,
        location=sensor.location,
        created_at=sensor.created_at,
        model=sensor.model
    )

    logger.info(f"Dispatching 'SENSOR_CREATED' event for sensor {sensor.sensor_id}")
    await dispatcher.dispatch(WebhookEvent.SENSOR_CREATED, payload)
    return sensor


async def get_sensor_by_id(sensor_id: UUID):
    """
    Fetch a sensor by its ID or raise a 404-style domain exception.
    """
    sensor = await sensor_repository.fetch_sensor_by_id(sensor_id)
    if not sensor:
        logger.warning(f"Sensor with ID={sensor_id} not found.")
        raise SensorNotFoundError(sensor_id)
    return sensor



async def safe_get_sensor_by_id(sensor_id: UUID) -> Sensor | None:
    """
    Wrapper for get_sensor_by_id that catches not-found errors silently.
    Useful in event-driven flows.
    """
    try:
        return await get_sensor_by_id(sensor_id)
    except SensorNotFoundError:
        return None



async def list_sensors():
    """
    Return all sensors in the system (unfiltered).
    """
    sensors = await sensor_repository.fetch_all_sensors()
    logger.debug(f"Fetched {len(sensors)} sensors from DB.")
    return sensors


async def update_sensor(sensor_id: UUID, update_data: SensorUpdate) -> SensorOut:
    """
    Update sensor metadata and dispatch SENSOR_STATUS_CHANGED webhook if successful.

    Raises:
        SensorNotFoundError if the sensor doesn't exist.
    """
    sensor = await sensor_repository.modify_sensor(sensor_id, update_data)
    if not sensor:
        logger.warning(f"Tried to update sensor {sensor_id}, but it doesn't exist.")
        raise SensorNotFoundError(sensor_id)

    sensor_out = SensorOut.model_validate(sensor)

    logger.info(f"Sensor {sensor_id} updated. Dispatching 'SENSOR_STATUS_CHANGED' event.")
    await dispatcher.dispatch(WebhookEvent.SENSOR_STATUS_CHANGED, sensor_out)
    return sensor_out



async def delete_sensor(sensor_id: UUID):
    """
    Delete a sensor by ID and dispatch SENSOR_DELETED event.

    Returns:
        True if successful, raises error otherwise.
    """
    success = await sensor_repository.remove_sensor(sensor_id)
    if not success:
        logger.warning(f"Tried to delete sensor {sensor_id}, but it doesn't exist.")
        raise SensorNotFoundError(sensor_id)

    logger.info(f"Sensor {sensor_id} deleted. Dispatching 'SENSOR_DELETED' event.")
    await dispatcher.dispatch(
        WebhookEvent.SENSOR_DELETED,
        SensorDeletedPayload(sensor_id=sensor_id, deleted_at=datetime.now(timezone.utc))
    )
    return True



async def list_sensors_with_placeholder() -> list[SensorOut]:
    """
    Retrieve all placeholder sensors — identified by name == "UNKNOWN".
    """
    all_sensors = await sensor_repository.fetch_all_sensors()
    placeholders = [SensorOut.model_validate(s) for s in all_sensors if s.name == "UNKNOWN"]
    logger.debug(f"Found {len(placeholders)} placeholder sensors.")
    return placeholders


async def query_sensor_metadata_advanced(payload: SensorMetadataQuery):
    """
    Run an advanced GraphQL-style metadata query with filters like:
    - Location
    - Model
    - Name
    - Created/Updated timestamps

    Returns paginated results.
    """
    query = await sensor_metadata_graphql_repository.build_sensor_metadata_query(payload)
    logger.info(f"Executing metadata query | page={payload.page} | page_size={payload.page_size}")
    return await paginate_query(
        query,
        page=payload.page,
        schema=SensorOut,
        page_size=payload.page_size or settings.DEFAULT_PAGE_SIZE
    )
