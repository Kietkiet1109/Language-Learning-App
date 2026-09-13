"""Application configuration loaded from the backend environment file."""

from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIRECTORY = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIRECTORY / ".env")

class Settings(BaseSettings):
    """Define configuration required by the backend service."""

    database_url: str
    frontend_origin: str = Field(
        default="http://localhost:3000",
        validation_alias="FRONTEND_URL",
    )
    whisper_model: str = "small"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
