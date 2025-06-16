from sqlalchemy import select, and_, or_, desc
from sqlalchemy.sql import Select
from typing import Optional
from uuid import UUID

from app.models.DB_tables.sensor_data import SensorData
from app.models.DB_tables.sensor import Sensor
from app.models.schemas.graphQL.SensorDataAdvancedQuery import SensorDataAdvancedQuery
from app.infrastructure.database.transaction import run_in_transaction


async def build_sensor_data_query(payload: SensorDataAdvancedQuery) -> Select:
    filters = []
    query = select(SensorData).order_by(desc(SensorData.timestamp))

    # Sensor ID filter
    if payload.sensor_ids:
        filters.append(SensorData.device_id.in_(payload.sensor_ids))

    # Timestamp range or exact match
    if payload.timestamps:
        filters.append(SensorData.timestamp.in_(payload.timestamps))
    else:
        if payload.timestamp_range_start:
            filters.append(SensorData.timestamp >= payload.timestamp_range_start)
        if payload.timestamp_range_end:
            filters.append(SensorData.timestamp <= payload.timestamp_range_end)

    # Field ranges
    for field, bounds in (payload.field_ranges or {}).items():
        column = getattr(SensorData, field, None)
        if column:
            min_val, max_val = bounds
            if min_val is not None:
                filters.append(column >= min_val)
            if max_val is not None:
                filters.append(column <= max_val)

    # Metadata filters: these require joining with Sensor table
    metadata_filters = []

    if payload.locations:
        metadata_filters.append(Sensor.location.in_(payload.locations))

    if payload.models:
        metadata_filters.append(Sensor.model.in_(payload.models))

    if payload.is_active is not None:
        metadata_filters.append(Sensor.is_active == payload.is_active)

    if metadata_filters:
        query = query.join(Sensor, Sensor.sensor_id == SensorData.device_id)
        filters.extend(metadata_filters)

    if filters:
        query = query.where(and_(*filters))

    return query
