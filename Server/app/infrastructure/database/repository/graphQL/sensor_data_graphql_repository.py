from sqlalchemy import select, and_, desc
from sqlalchemy.sql import Select
from typing import Optional
from uuid import UUID

from app.models.DB_tables.sensor_data import SensorData
from app.models.DB_tables.sensor import Sensor
from app.models.schemas.graphQL.Sensor_data_query import SensorDataAdvancedQuery


async def build_sensor_data_query(payload: SensorDataAdvancedQuery) -> Select:
    """
    Build a SQLAlchemy query for sensor data based on GraphQL filter inputs.

    Args:
        payload (SensorDataAdvancedQuery): Input filter criteria from GraphQL query.

    Returns:
        sqlalchemy.sql.Select: SQLAlchemy query object ready for execution.

    Supports:
    - Sensor ID filtering (one or many)
    - Timestamp filters (exact list or range)
    - Per-field value ranges (min, max)
    - Metadata filters (model, location, is_active)
    - Auto-joins with Sensor table when metadata filters are present

    Notes:
    - Query results are ordered by timestamp descending.
    - This builder is used by GraphQL resolvers and returns only the raw query.
    """

    filters = []

    # Base query on SensorData table, ordered by most recent first
    query = select(SensorData).order_by(desc(SensorData.timestamp))

    # ──────────────────────── Sensor ID Filter ────────────────────────
    if payload.sensor_ids:
        filters.append(SensorData.device_id.in_(payload.sensor_ids))

    # ──────────────────────── Timestamp Filters ────────────────────────
    if payload.timestamps:
        # Exact timestamp matching
        filters.append(SensorData.timestamp.in_(payload.timestamps))
    else:
        # Range-based filtering
        if payload.timestamp_range_start:
            filters.append(SensorData.timestamp >= payload.timestamp_range_start)
        if payload.timestamp_range_end:
            filters.append(SensorData.timestamp <= payload.timestamp_range_end)

    # ──────────────────────── Field-Specific Ranges ────────────────────────
    if payload.field_ranges:
        for field, (min_val, max_val) in payload.field_ranges.items():
            column = getattr(SensorData, field, None)
            if column is not None:
                if min_val is not None:
                    filters.append(column >= min_val)
                if max_val is not None:
                    filters.append(column <= max_val)

    # ──────────────────────── Sensor Metadata Filters ────────────────────────
    metadata_filters = []

    if payload.locations:
        metadata_filters.append(Sensor.location.in_(payload.locations))

    if payload.models:
        metadata_filters.append(Sensor.model.in_(payload.models))

    if payload.is_active is not None:
        metadata_filters.append(Sensor.is_active == payload.is_active)

    # ───── Join with Sensor table if any metadata filters are used ─────
    if metadata_filters:
        query = query.join(Sensor, Sensor.sensor_id == SensorData.device_id)
        filters.extend(metadata_filters)

    # ──────────────────────── Final Filter Application ────────────────────────
    if filters:
        query = query.where(and_(*filters))

    return query
