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
    DEFAULT_USER_PASSWORD: str = "ChangeMe123!"

    # ─── JWT Settings ────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # ─── User Secret Settings ────────────────────────────
    USER_SECRET_LENGTH: int = 32
    USER_SECRET_EXPIRATION_DAYS: int = 180
    MAX_SECRETS_PER_USER: int = 3  # active only

    # ─── API Key Settings ────────────────────────────────
    API_KEY_LENGTH: int = 32
    API_KEY_EXPIRATION_DAYS: int = 90
    MAX_API_KEYS_PER_USER: int = 5  # active only

    # ─── Admin Bootstrap ─────────────────────────────
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: SecretStr

    # ─── Pagination Settings ────────────────────────────────
    DEFAULT_PAGE_SIZE: int
    MAX_PAGE_SIZE: int  # Maximum allowed page size for queries

    # ─── MQTT Settings ───────────────────────────────────────
    MQTT_BROKER: str
    MQTT_PORT: int
    MQTT_TOPIC: str
    MQTT_QOS: int
    MQTT_RECONNECT_TIMER: int

    # ─── MQTT Auth Settings ─────────────────────────────────
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None

    # Go three levels up: utils → app → Server → .env
    project_root: ClassVar[Path] = Path(__file__).resolve().parents[2]
    env_file_path: ClassVar[Path] = project_root / ".env"

    model_config = SettingsConfigDict(
        env_file=str(env_file_path),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    if not env_file_path.exists():
        logger.warning(f".env file NOT found at: {env_file_path}")
    else:
        logger.info(f".env loaded from: {env_file_path}")

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


# Try to load the settings
try:
    settings = Settings() # type: ignore
except ValidationError as e:
    logger.error(f"Validation error in settings: {e}")
    settings = None
except Exception as e:
    logger.warning(f"Could not load settings from .env file or environment: {e}")
    settings = None
