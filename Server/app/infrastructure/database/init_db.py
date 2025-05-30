from .session import engine
from .base import Base
from .models import (
    user_secrets,
    rate_limits,
    user,
    graphql_logs,
    websocket_logs,
    webhook_logs,
    rest_logs,
    api_keys,
    sensor_data)

import logging
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables checked and initialized.")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize the database: {e}")
    except Exception as ex:
        logger.error(f" Unexpected error during DB init: {ex}")
