from pathlib import Path
from pydantic import BaseModel, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
from typing import ClassVar
import os

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ─── Environment Setup ───────────────────────────────
    ENV: str = Field(default="local")  # or "docker"
    DATABASE_URL: str | None = None
    DATABASE_URL_LOCAL: str | None = None
    API_VERSION: str

    # ─── Default Password ────────────────────────────────
    DEFAULT_USER_PASSWORD: SecretStr

    # ─── JWT Settings ────────────────────────────────────
    JWT_ALGORITHM: str
    JWT_EXPIRATION_MINUTES: int

    # ─── User Secret Settings ────────────────────────────
    USER_SECRET_LENGTH: int
    USER_SECRET_EXPIRATION_DAYS: int
    MAX_SECRETS_PER_USER: int
    MASTER_ENCRYPTION_KEY: SecretStr

    # ─── API Key Settings ────────────────────────────────
    API_KEY_LENGTH: int
    API_KEY_EXPIRATION_DAYS: int
    MAX_API_KEYS_PER_USER: int

    # ─── Admin Bootstrap ─────────────────────────────
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: SecretStr

    # ─── Pagination Settings ────────────────────────────────
    DEFAULT_PAGE_SIZE: int
    MAX_PAGE_SIZE: int

    # ─── MQTT Settings ───────────────────────────────────────
    MQTT_BROKER: str
    MQTT_PORT: int
    MQTT_SENSOR_DATA_TOPIC: str
    MQTT_SENSOR_STATUS_TOPIC: str
    MQTT_SENSOR_STATUS_TOPICSt_START_WITH: str
    MQTT_QOS: int
    MQTT_RECONNECT_TIMER: int

    # ─── MQTT Auth Settings ─────────────────────────────────
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None

    # ─── Webhook const ─────────────────────────────────
    MAX_ATTEMPTS_PER_WEBHOOK: int

    # ─── Rate Limit Settings ─────────────────────────────
    REST_RATE_LIMIT: str
    LOGIN_RATE_LIMIT: str
    ADMIN_AUTH_RATE_LIMIT: str
    AUTH_RATE_LIMIT: str
    SENSOR_PUBLIC_RATE_LIMIT: str
    SENSOR_QUERY_RATE_LIMIT: str
    SENSOR_CREATE_RATE_LIMIT: str
    SENSOR_META_QUERY_RATE_LIMIT: str
    SENSOR_META_ADMIN_RATE_LIMIT: str
    SENSOR_MQTT_MONITOR_RATE_LIMIT: str
    GRAPHQL_DATA_QUERY_LIMIT: str
    GRAPHQL_META_QUERY_LIMIT: str
    WEBHOOK_QUERY_RATE_LIMIT: str
    WEBHOOK_WRITE_RATE_LIMIT: str

    # ─── File & Path Settings ───────────────────────────────
    project_root: ClassVar[Path] = Path(__file__).resolve().parents[2]
    env_file_path: ClassVar[Path] = project_root / ".env"

    model_config = SettingsConfigDict(
        env_file=str(env_file_path),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def active_database_url(self) -> str:
        if self.ENV == "docker":
            if not self.DATABASE_URL:
                raise ValueError("DATABASE_URL must be set when ENV=docker")
            return self.DATABASE_URL
        else:
            if not self.DATABASE_URL_LOCAL:
                raise ValueError("DATABASE_URL_LOCAL must be set when ENV=local")
            return self.DATABASE_URL_LOCAL


# ─── Initialization ─────────────────────────────────────────
try:
    settings = Settings()  # type: ignore
    logger.info(f".env loaded from: {Settings.env_file_path}")
except ValidationError as e:
    logger.error(f"Validation error in settings: {e}")
    settings = None
except Exception as e:
    logger.warning(f"Could not load settings from .env or environment: {e}")
    settings = None
