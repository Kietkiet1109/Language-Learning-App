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
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    translation_model: str = "Helsinki-NLP/opus-mt-fr-en"
    translation_device: str = "cpu"
    recording_directory: str = str(BACKEND_DIRECTORY / "recordings")
    max_recording_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
