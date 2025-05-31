from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_core import PydanticUndefined
import os
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., description="Database URL")  # required
    API_VERSION: str = "v1"  # optional, defaults to v1

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env") if (Path(__file__).parent.parent / ".env").exists() else None,
        env_file_encoding="utf-8"
    )


# Try to load settings and handle missing file gracefully
try:
    settings = Settings()  # type: ignore
except Exception as e:
    logger.warning(f"Could not load settings from .env file or environment: {e}")
    settings = None
