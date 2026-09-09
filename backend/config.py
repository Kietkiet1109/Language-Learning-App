"""Application configuration loaded from the backend environment file."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIRECTORY = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Define configuration required by the backend service."""

    database_url: str
    frontend_origin: str = "http://localhost:3000"
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
    facebook_redirect_uri: str = (
        "http://localhost:8000/auth/facebook/callback"
    )
    facebook_graph_version: str = "v24.0"
    facebook_state_cookie_name: str = "facebook_oauth_state"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
