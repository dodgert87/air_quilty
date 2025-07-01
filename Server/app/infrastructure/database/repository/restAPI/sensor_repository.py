from datetime import datetime, timezone
from sqlalchemy import select
from uuid import UUID
from app.models.DB_tables.sensor import Sensor
from app.infrastructure.database.transaction import run_in_transaction
from app.models.schemas.rest.sensor_schemas import SensorCreate, SensorUpdate
from app.utils.exceptions_base import AppException


async def insert_sensor(sensor_data: SensorCreate) -> Sensor:
    """
    Insert a new sensor into the system.

    Args:
        sensor_data (SensorCreate): Validated Pydantic model.

    Returns:
        Sensor: The newly inserted sensor row.

    Raises:
        AppException: If sensor already exists or DB error occurs.
    """
    try:
        async with run_in_transaction() as session:
            # Check for duplicate sensor ID
            result = await fetch_sensor_by_id(sensor_data.sensor_id)
            if result:
                raise AppException(
                    message=f"Sensor with ID {sensor_data.sensor_id} already exists.",
                    status_code=409,
                    public_message="Sensor already exists.",
                    domain="sensor"
                )

            sensor = Sensor(**sensor_data.model_dump())
            session.add(sensor)
            return sensor

    except AppException:
        raise  # Allow propagation of intentionally raised exception

    except Exception as e:
        raise AppException(
            message=f"DB insert failed: {e}",
            status_code=500,
            public_message="Failed to save sensor.",
            domain="sensor"
        )


async def fetch_sensor_by_id(sensor_id: UUID) -> Sensor | None:
    """
    Retrieve a sensor by its UUID.

    Returns:
        Sensor | None: Matching row or None.

    Raises:
        AppException: On DB failure.
    """
    try:
        async with run_in_transaction() as session:
            return await session.get(Sensor, sensor_id)
    except Exception as e:
        raise AppException(
            message=f"DB fetch failed for sensor {sensor_id}: {e}",
            status_code=500,
            public_message="Failed to retrieve sensor.",
            domain="sensor"
        )



async def fetch_all_sensors() -> list[Sensor]:
    """
    Retrieve all sensors, sorted by creation time descending.

    Returns:
        List[Sensor]: All sensor records.

    Raises:
        AppException: On DB error.
    """
    try:
        async with run_in_transaction() as session:
            result = await session.execute(
                select(Sensor).order_by(Sensor.created_at.desc())
            )
            return list(result.scalars().all())
    except Exception as e:
        raise AppException(
            message=f"DB fetch-all failed: {e}",
            status_code=500,
            public_message="Failed to load sensors.",
            domain="sensor"
        )



async def modify_sensor(sensor_id: UUID, update_data: SensorUpdate) -> Sensor | None:
    """
    Update fields in a sensor. Fields not set will be ignored.

    Args:
        sensor_id (UUID): Sensor to modify.
        update_data (SensorUpdate): Fields to update.

    Returns:
        Sensor | None: Updated sensor or None if not found.

    Raises:
        AppException: On DB error.
    """
    try:
        async with run_in_transaction() as session:
            sensor = await session.get(Sensor, sensor_id)
            if not sensor:
                return None

            for field, value in update_data.model_dump(exclude_unset=True).items():
                setattr(sensor, field, value)

            sensor.updated_at = datetime.now(timezone.utc)
            return sensor
    except Exception as e:
        raise AppException(
            message=f"Failed to update sensor {sensor_id}: {e}",
            status_code=500,
            public_message="Failed to update sensor.",
            domain="sensor"
        )



async def remove_sensor(sensor_id: UUID) -> bool:
    """
    Delete a sensor from the system.

    Args:
        sensor_id (UUID): Target sensor to delete.

    Returns:
        bool: True if deleted, False if sensor not found.

    Raises:
        AppException: On DB error.
    """
    try:
        async with run_in_transaction() as session:
            sensor = await session.get(Sensor, sensor_id)
            if not sensor:
                return False

            await session.delete(sensor)
            return True
    except Exception as e:
        raise AppException(
            message=f"Failed to delete sensor {sensor_id}: {e}",
            status_code=500,
            public_message="Failed to delete sensor.",
            domain="sensor"
        )

