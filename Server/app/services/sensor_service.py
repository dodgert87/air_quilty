from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from app.models.sensor import SensorData, SensorDataIn

async def get_latest_sensor_data(db: AsyncSession, limit: int = 100):
    result = await db.execute(
        select(SensorData).order_by(desc(SensorData.timestamp)).limit(limit)
    )
    return result.scalars().all()

async def insert_sensor_data(db: AsyncSession, data: SensorDataIn):
    new_entry = SensorData(**data.model_dump())
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)
    return new_entry
