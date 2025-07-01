from typing import Sequence
from datetime import datetime
from sqlalchemy import and_, select
from app.models.schemas.graphQL.sensor_meta_data_query import SensorMetadataQuery
from app.models.DB_tables.sensor import Sensor


class sensor_metadata_graphql_repository:
    """
    Repository responsible for building SQLAlchemy queries for sensor metadata,
    based on input from GraphQL queries (SensorMetadataQuery).
    """

    @staticmethod
    async def build_sensor_metadata_query(payload: SensorMetadataQuery):
        """
        Construct a filtered SQLAlchemy SELECT query for sensor metadata.

        Args:
            payload (SensorMetadataQuery): Input query filters from GraphQL layer.

        Returns:
            sqlalchemy.sql.Select: A filtered SELECT query on the Sensor table.

        Supported Filters:
        - sensor_ids: List[UUID]
        - name_filter: List[str]
        - locations: List[str]
        - models: List[str]
        - is_active: Optional[bool]
        - created_at: { after, before } timestamps
        - updated_at: { after, before } timestamps
        """

        stmt = select(Sensor)
        filters = []

        # ──────────────────────── Sensor ID Filters ────────────────────────
        if payload.sensor_ids:
            filters.append(Sensor.sensor_id.in_(payload.sensor_ids))

        # ──────────────────────── Sensor Name Filter ────────────────────────
        if payload.name_filter:
            filters.append(Sensor.name.in_(payload.name_filter))

        # ──────────────────────── Location Filter ────────────────────────
        if payload.locations:
            filters.append(Sensor.location.in_(payload.locations))

        # ──────────────────────── Model Filter ────────────────────────
        if payload.models:
            filters.append(Sensor.model.in_(payload.models))

        # ──────────────────────── Activation Status Filter ────────────────────────
        if payload.is_active is not None:
            filters.append(Sensor.is_active == payload.is_active)

        # ──────────────────────── Created At Range Filter ────────────────────────
        if payload.created_at:
            if payload.created_at.after:
                filters.append(Sensor.created_at >= payload.created_at.after)
            if payload.created_at.before:
                filters.append(Sensor.created_at <= payload.created_at.before)

        # ──────────────────────── Updated At Range Filter ────────────────────────
        if payload.updated_at:
            if payload.updated_at.after:
                filters.append(Sensor.updated_at >= payload.updated_at.after)
            if payload.updated_at.before:
                filters.append(Sensor.updated_at <= payload.updated_at.before)

        # ──────────────────────── Final WHERE Clause ────────────────────────
        if filters:
            stmt = stmt.where(and_(*filters))

        return stmt
