from uuid import UUID
from sqlalchemy import desc, select, and_
from app.models.sensor_data import SensorData
from app.models.sensor_data_schemas import SensorDataIn, SensorRangeQuery, SensorTimestampQuery
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.exceptions_base import AppException


async def search_by_attribute_ranges(payload: SensorRangeQuery):
    filters = []
    selected_columns = [SensorData.timestamp, SensorData.device_id]

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
    query = select(SensorData).where(SensorData.device_id == sensor_id).order_by(SensorData.timestamp.desc())
    return query
