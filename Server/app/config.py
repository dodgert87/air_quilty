from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import os

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    ENV: str = Field(default="local")  # or "docker"

    DATABASE_URL: str | None = None
    DATABASE_URL_LOCAL: str | None = None
    API_VERSION: str = "v1"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
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


try:
    settings = Settings()
except ValidationError as e:
    logger.error(f"Validation error in settings: {e}")
    settings = None
except Exception as e:
    logger.warning(f"Could not load settings from .env file or environment: {e}")
    settings = None
