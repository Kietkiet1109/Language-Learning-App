"""Email delivery for account recovery messages."""

from email.message import EmailMessage
import aiosmtplib
from backend.config import settings


async def send_password_reset_code(email: str, code: str) -> None:
    """Send a password-reset verification code through configured SMTP."""

    if not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError(
            "SMTP password-reset email settings are incomplete."
        )

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message["Subject"] = "Your Prononcia password reset code"
    message.set_content(
        "Your Prononcia verification code is "
        f"{code}. It expires in "
        f"{settings.password_reset_expiry_minutes} minutes."
    )

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        start_tls=settings.smtp_start_tls,
    )
