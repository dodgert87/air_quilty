
from pathlib import Path
from pydantic_settings import BaseSettings,  SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=str(Path(__file__).parent.parent / ".env"))

settings = Settings() # type: ignore
#print(f"Loaded DATABASE_URL: {settings.DATABASE_URL}")
