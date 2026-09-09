"""Authentication helpers for password hashing and session management."""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from pwdlib import PasswordHash
from backend.config import settings


password_hasher = PasswordHash.recommended()


PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])"
    r"(?=.*[^A-Za-z0-9]).{8,128}$"
)

def hash_password(password: str) -> str:
    """Hash a password with the configured password hashing algorithm."""

    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain-text password against its stored hash."""

    return password_hasher.verify(password, password_hash)


def is_password_strong(password: str) -> bool:
    """Return whether a password meets the application's password rules."""

    return PASSWORD_PATTERN.fullmatch(password) is not None


def hash_reset_token(token: str) -> str:
    """Hash a password-reset code or reset credential for database storage."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session_token() -> tuple[str, str, datetime]:
    """Create a raw token, its database hash, and its expiry timestamp."""

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(
        days=settings.session_expiry_days,
    )
    return raw_token, token_hash, expires_at
