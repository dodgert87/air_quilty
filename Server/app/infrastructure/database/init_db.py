from app.utils.crypto_utils import encrypt_secret
from app.utils.logging_config import setup_logging
setup_logging()

import logging
from sqlalchemy.exc import SQLAlchemyError
from app.infrastructure.database.repository.restAPI import secret_repository, user_repository
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.hashing import hash_value
from app.utils.secret_utils import generate_secret, get_secret_expiry
from app.utils.config import settings
from .session import engine
from app.models.DB_tables.base import Base

from app.models.DB_tables.sensor_data import SensorData
from app.models.DB_tables.user import RoleEnum, User
from app.models.DB_tables.api_keys import APIKey
from app.models.DB_tables.rate_limits import RateLimit
from app.models.DB_tables.user_secrets import UserSecret
from app.models.DB_tables.webhook_logs import WebhookLog
from app.models.DB_tables.rest_logs import RestLog
from app.models.DB_tables.graphql_logs import GraphQLLog
from app.models.DB_tables.sensor import Sensor
from app.models.DB_tables.webhook import Webhook

logger = logging.getLogger(__name__)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables checked and initialized.")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize the database: {e}")
        return
    except Exception as ex:
        logger.error(f"Unexpected error during DB init: {ex}")
        return

    # Bootstrap admin user
    try:
        async with run_in_transaction() as session:
            existing = await user_repository.get_user_by_email(session, settings.ADMIN_EMAIL)
            if existing:
                logger.info("Admin user already exists.")
                return

            logger.info("Creating default admin user...")

            hashed_pw = hash_value(settings.ADMIN_PASSWORD.get_secret_value())

            admin_user = await user_repository.create_user(
                session,
                email=settings.ADMIN_EMAIL,
                username="admin",
                hashed_password=hashed_pw,
                role=RoleEnum.admin
            )

            await secret_repository.create_user_secret(
                session,
                user_id=admin_user.id,
                secret=encrypt_secret(generate_secret()),
                label="admin-init",
                is_active=True,
                expires_at=get_secret_expiry()
            )

            logger.info(f"Default admin user initialized: {settings.ADMIN_EMAIL}")

    except Exception as ex:
        logger.error(f"Failed to initialize admin user: {ex}")
