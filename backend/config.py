"""Application configuration loaded from the backend environment file."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIRECTORY = Path(__file__).resolve().parent

class Settings(BaseSettings):
    """Define configuration required by the backend service."""

    database_url: str

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
