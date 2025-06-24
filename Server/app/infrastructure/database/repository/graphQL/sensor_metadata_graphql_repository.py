from typing import Sequence
from sqlalchemy import and_, select
from app.models.schemas.graphQL.sensor_meta_data_query import SensorMetadataQuery
from app.models.DB_tables.sensor import Sensor
from datetime import datetime


class sensor_metadata_graphql_repository:
    @staticmethod
    async def build_sensor_metadata_query(payload: SensorMetadataQuery):
        stmt = select(Sensor)
        filters = []

        # ───── ID Filters ─────
        if payload.sensor_ids:
            filters.append(Sensor.sensor_id.in_(payload.sensor_ids))

        # ───── Name Filter ─────
        if payload.name_filter:
            filters.append(Sensor.name.in_(payload.name_filter))

        # ───── Location Filter ─────
        if payload.locations:
            filters.append(Sensor.location.in_(payload.locations))

        # ───── Model Filter ─────
        if payload.models:
            filters.append(Sensor.model.in_(payload.models))

        # ───── Active Status Filter ─────
        if payload.is_active is not None:
            filters.append(Sensor.is_active == payload.is_active)

        # ───── Created At Range ─────
        if payload.created_at:
            if payload.created_at.after:
                filters.append(Sensor.created_at >= payload.created_at.after)
            if payload.created_at.before:
                filters.append(Sensor.created_at <= payload.created_at.before)

        # ───── Updated At Range ─────
        if payload.updated_at:
            if payload.updated_at.after:
                filters.append(Sensor.updated_at >= payload.updated_at.after)
            if payload.updated_at.before:
                filters.append(Sensor.updated_at <= payload.updated_at.before)

        # ───── Apply Filters ─────
        if filters:
            stmt = stmt.where(and_(*filters))

        return stmt
