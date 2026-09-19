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
      
    session_cookie_name: str = "prononcia_session"
    session_cookie_secure: bool = False
    session_expiry_days: int = 30
    password_reset_expiry_minutes: int = 10
      
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_start_tls: bool = True
      
    facebook_app_id: str | None = None
    facebook_app_secret: str | None = None
    facebook_redirect_uri: str = Field(
        default="http://localhost:8000/auth/facebook/callback",
        validation_alias="FACEBOOK_REDIRECT_URI",
    )
    facebook_graph_version: str = "v24.0"
    facebook_state_cookie_name: str = "facebook_oauth_state"
      
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = (
        default="http://localhost:8000/auth/google/callback",
        validation_alias="GOOGLE_REDIRECT_URI",
    )
    google_state_cookie_name: str = "google_oauth_state"
    google_nonce_cookie_name: str = "google_oauth_nonce"
      
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
