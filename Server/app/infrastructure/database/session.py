from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.utils.config import settings

engine = create_async_engine(settings.active_database_url, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
