from uuid import UUID
from sqlalchemy import desc, select, and_
from app.models.DB_tables.sensor_data import SensorData
from app.models.schemas.rest.sensor_data_schemas import SensorDataIn, SensorRangeQuery, SensorTimestampQuery
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.exceptions_base import AppException


async def search_by_attribute_ranges(payload: SensorRangeQuery):
    """
    Build a query to search sensor data by any combination of field ranges.

    Always includes `timestamp` and `device_id` in the result.

    Args:
        payload (SensorRangeQuery): A dictionary of fields → [min, max] bounds.

    Returns:
        SQLAlchemy Select: Executable query object.
    """
    filters = []
    selected_columns = [SensorData.timestamp, SensorData.device_id]  # Always included

    for attr, bounds in payload.ranges.items():
        column = getattr(SensorData, attr)
        selected_columns.append(column)
        min_val, max_val = bounds
        if min_val is not None:
            filters.append(column >= min_val)
        if max_val is not None:
            filters.append(column <= max_val)

    query = select(*selected_columns).order_by(SensorData.timestamp.desc())

    if filters:
        query = query.where(and_(*filters))

    return query



async def insert_sensor_data(payload: SensorDataIn) -> SensorData:
    """
    Insert a new sensor data row into the database.

    Args:
        payload (SensorDataIn): Sensor input model (validated).

    Returns:
        SensorData: Inserted SQLAlchemy object (not committed yet).

    Raises:
        AppException: On any failure to insert.
    """
    try:
        async with run_in_transaction() as session:
            entry = SensorData(**payload.model_dump())
            session.add(entry)
            return entry
    except Exception as e:
        raise AppException(
            message=f"Failed to insert sensor data: {e}",
            status_code=500,
            public_message="Internal error while saving sensor data.",
            domain="sensor"
        )



async def fetch_latest_by_sensor(sensor_id: UUID) -> SensorData | None:
    """
    Fetch the latest recorded data point for a specific sensor.

    Args:
        sensor_id (UUID): Sensor UUID.

    Returns:
        SensorData | None: Most recent entry or None if no data.
    """
    async with run_in_transaction() as session:
        query = (
            select(SensorData)
            .where(SensorData.device_id == str(sensor_id))
            .order_by(desc(SensorData.timestamp))
            .limit(1)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def search_by_timestamps(payload: SensorTimestampQuery):
    """
    Search sensor data by timestamp(s).

    If `exact=True`, matches provided timestamps exactly.
    If `exact=False`, expects exactly two timestamps to define a range.

    Raises:
        AppException: If range query has incorrect format.

    Returns:
        SQLAlchemy Select: Query filtered by timestamp.
    """
    if not payload.exact and len(payload.timestamps) != 2:
        raise AppException(
            message="For ranged timestamp queries, provide exactly two timestamps.",
            status_code=400,
            public_message="Expected exactly 2 timestamps for ranged query.",
            domain="sensor"
        )

    base_query = select(SensorData).order_by(SensorData.timestamp.desc())

    if payload.exact:
        base_query = base_query.where(SensorData.timestamp.in_(payload.timestamps))
    else:
        start, end = sorted(payload.timestamps)
        base_query = base_query.where(and_(
            SensorData.timestamp >= start,
            SensorData.timestamp <= end
        ))

    return base_query



async def search_by_sensor_id(sensor_id: UUID):
    """
    Fetch full sensor history by sensor ID, sorted by timestamp descending.

    Args:
        sensor_id (UUID): Device UUID.

    Returns:
        SQLAlchemy Select: Full history query.
    """
    return select(SensorData).where(
        SensorData.device_id == sensor_id
    ).order_by(SensorData.timestamp.desc())
