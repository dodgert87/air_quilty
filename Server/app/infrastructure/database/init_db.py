from .session import engine
from app.models.base import Base

from app.models.sensor import SensorData
from app.models.user import User
from app.models.api_keys import APIKey
from app.models.rate_limits import RateLimit
from app.models.user_secrets import UserSecret
from app.models.webhook_logs import WebhookLog
from app.models.rest_logs import RestLog
from app.models.graphql_logs import GraphQLLog



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
