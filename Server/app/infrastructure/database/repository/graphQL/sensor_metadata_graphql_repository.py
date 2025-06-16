from typing import Sequence
from sqlalchemy import and_, select
from app.models.schemas.graphQL.sensor_meta_data_query import SensorMetadataQuery
from app.models.DB_tables.sensor import Sensor
from app.models.schemas.rest.sensor_schemas import SensorOut
from app.infrastructure.database.transaction import run_in_transaction
from app.domain.pagination import paginate_query
from datetime import datetime


class sensor_metadata_graphql_repository:
    @staticmethod
    async def build_sensor_metadata_query(payload: SensorMetadataQuery):
        stmt = select(Sensor)
        filters = []

        # ID filters
        if payload.sensor_ids:
            filters.append(Sensor.sensor_id.in_(payload.sensor_ids))

        # Name filter
        if payload.name_filter:
            filters.append(Sensor.name.in_(payload.name_filter))

        # Location filter
        if payload.locations:
            filters.append(Sensor.location.in_(payload.locations))

        # Model filter
        if payload.models:
            filters.append(Sensor.model.in_(payload.models))

        # is_active filter
        if payload.is_active is not None:
            filters.append(Sensor.is_active == payload.is_active)

        # created_at range
        if payload.created_at:
            if payload.created_at.after:
                filters.append(Sensor.created_at >= payload.created_at.after)
            if payload.created_at.before:
                filters.append(Sensor.created_at <= payload.created_at.before)

        # updated_at range
        if payload.updated_at:
            if payload.updated_at.after:
                filters.append(Sensor.updated_at >= payload.updated_at.after)
            if payload.updated_at.before:
                filters.append(Sensor.updated_at <= payload.updated_at.before)

        if filters:
            stmt = stmt.where(and_(*filters))
        return stmt

