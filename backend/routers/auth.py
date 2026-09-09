"""Authentication endpoints for account creation and login."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from aiosmtplib.errors import SMTPException
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import (
    create_session_token,
    hash_password,
    hash_reset_token,
    is_password_strong,
    verify_password,
)
from backend.config import settings
from backend.database import get_database_session
from backend.mailer import send_password_reset_code
from backend.schemas import (
    AuthResponse,
    AuthUser,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetMessage,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    PasswordResetVerifyResponse,
    SignupRequest,
)


router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    """Normalize email input before validation and database lookup."""

    return email.strip().lower()


def normalize_name(name: str) -> str:
    """Remove accidental whitespace from a user's display name."""

    return " ".join(name.split())


async def create_session(
    session: AsyncSession,
    user_id: str,
    response: Response,
) -> None:
    """Persist a hashed session token and set its secure cookie."""

    raw_token, token_hash, expires_at = create_session_token()
    await session.execute(
        text(
            """
            INSERT INTO user_sessions (user_id, token_hash, expires_at)
            VALUES (:user_id, :token_hash, :expires_at)
            """
        ),
        {
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
        },
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_expiry_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    payload: SignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_database_session),
) -> AuthResponse:
    """Validate, hash, persist, and sign in a new user."""

    name = normalize_name(payload.name)
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name cannot be blank.",
        )

    email = normalize_email(str(payload.email))
    if not is_password_strong(payload.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Password must contain 8-128 characters, an uppercase "
                "letter, a lowercase letter, a number, and a symbol."
            ),
        )

    password_hash = hash_password(payload.password)

    try:
        result = await session.execute(
            text(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (:name, :email, :password_hash)
                RETURNING id, name, email
                """
            ),
            {
                "name": name,
                "email": email,
                "password_hash": password_hash,
            },
        )
        user = result.mappings().one()
        await create_session(session, str(user["id"]), response)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if "uq_users_email" in str(error.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            ) from error
        raise

    return AuthResponse(user=AuthUser(**user))


@router.post("/password-reset/request", response_model=PasswordResetMessage)
async def request_password_reset(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_database_session),
) -> PasswordResetMessage:
    """Generate and email a six-digit password-reset verification code."""

    email = normalize_email(str(payload.email))
    result = await session.execute(
        text("SELECT id FROM users WHERE email = :email AND is_active = true"),
        {"email": email},
    )
    user = result.mappings().one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active account was found for this email.",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.password_reset_expiry_minutes,
    )
    await session.execute(
        text(
            """
            UPDATE password_reset_tokens
            SET used_at = :used_at
            WHERE user_id = :user_id AND used_at IS NULL
            """
        ),
        {"used_at": datetime.now(UTC), "user_id": user["id"]},
    )
    await session.execute(
        text(
            """
            INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
            VALUES (:user_id, :token_hash, :expires_at)
            """
        ),
        {
            "user_id": user["id"],
            "token_hash": hash_reset_token(code),
            "expires_at": expires_at,
        },
    )
    await session.commit()

    try:
        await send_password_reset_code(email, code)
    except RuntimeError as error:
        logger.error("Password-reset SMTP configuration is incomplete.")
        await session.execute(
            text(
                """
                UPDATE password_reset_tokens
                SET used_at = :used_at
                WHERE user_id = :user_id AND token_hash = :token_hash
                """
            ),
            {
                "used_at": datetime.now(UTC),
                "user_id": user["id"],
                "token_hash": hash_reset_token(code),
            },
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password-reset email service is not configured.",
        ) from error
    except (OSError, SMTPException, TimeoutError) as error:
        logger.exception("Password-reset email delivery failed.")
        await session.execute(
            text(
                """
                UPDATE password_reset_tokens
                SET used_at = :used_at
                WHERE user_id = :user_id AND token_hash = :token_hash
                """
            ),
            {
                "used_at": datetime.now(UTC),
                "user_id": user["id"],
                "token_hash": hash_reset_token(code),
            },
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password-reset email could not be sent.",
        ) from error

    return PasswordResetMessage(message="Verification code sent.")


@router.post(
    "/password-reset/verify",
    response_model=PasswordResetVerifyResponse,
)
async def verify_password_reset(
    payload: PasswordResetVerifyRequest,
    session: AsyncSession = Depends(get_database_session),
) -> PasswordResetVerifyResponse:
    """Verify a reset code and exchange it for a one-time reset credential."""

    result = await session.execute(
        text(
            """
            SELECT password_reset_tokens.id, password_reset_tokens.token_hash,
                   password_reset_tokens.expires_at
            FROM password_reset_tokens
            JOIN users ON users.id = password_reset_tokens.user_id
            WHERE users.email = :email
              AND users.is_active = true
              AND password_reset_tokens.used_at IS NULL
            ORDER BY password_reset_tokens.created_at DESC
            LIMIT 1
            """
        ),
        {"email": normalize_email(str(payload.email))},
    )
    reset_record = result.mappings().one_or_none()
    is_valid = (
        reset_record is not None
        and reset_record["expires_at"] > datetime.now(UTC)
        and secrets.compare_digest(
            reset_record["token_hash"],
            hash_reset_token(payload.code),
        )
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification code is invalid or expired.",
        )

    reset_token = secrets.token_urlsafe(32)
    await session.execute(
        text(
            """
            UPDATE password_reset_tokens
            SET token_hash = :token_hash
            WHERE id = :token_id
            """
        ),
        {
            "token_hash": hash_reset_token(reset_token),
            "token_id": reset_record["id"],
        },
    )
    await session.commit()
    return PasswordResetVerifyResponse(reset_token=reset_token)


@router.post("/password-reset/confirm", response_model=PasswordResetMessage)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_database_session),
) -> PasswordResetMessage:
    """Hash and persist a new password after code verification."""

    if not is_password_strong(payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Password must contain 8-128 characters, an uppercase "
                "letter, a lowercase letter, a number, and a symbol."
            ),
        )

    result = await session.execute(
        text(
            """
            SELECT password_reset_tokens.id, password_reset_tokens.user_id
            FROM password_reset_tokens
            WHERE password_reset_tokens.token_hash = :token_hash
              AND password_reset_tokens.used_at IS NULL
              AND password_reset_tokens.expires_at > :now
            FOR UPDATE
            """
        ),
        {
            "token_hash": hash_reset_token(payload.reset_token),
            "now": datetime.now(UTC),
        },
    )
    reset_record = result.mappings().one_or_none()

    if reset_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password-reset session is invalid or expired.",
        )

    now = datetime.now(UTC)
    await session.execute(
        text(
            """
            UPDATE users
            SET password_hash = :password_hash, updated_at = :updated_at
            WHERE id = :user_id AND is_active = true
            """
        ),
        {
            "password_hash": hash_password(payload.new_password),
            "updated_at": now,
            "user_id": reset_record["user_id"],
        },
    )
    await session.execute(
        text(
            """
            UPDATE password_reset_tokens
            SET used_at = :used_at
            WHERE id = :token_id
            """
        ),
        {"used_at": now, "token_id": reset_record["id"]},
    )
    await session.execute(
        text(
            """
            UPDATE user_sessions
            SET revoked_at = :revoked_at
            WHERE user_id = :user_id AND revoked_at IS NULL
            """
        ),
        {"revoked_at": now, "user_id": reset_record["user_id"]},
    )
    await session.commit()
    return PasswordResetMessage(message="Password reset successfully.")


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_database_session),
) -> AuthResponse:
    """Authenticate a user and create a server-managed session."""

    result = await session.execute(
        text(
            """
            SELECT id, name, email, password_hash, is_active
            FROM users
            WHERE email = :email
            """
        ),
        {"email": normalize_email(str(payload.email))},
    )
    user = result.mappings().one_or_none()

    if user is None or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    await create_session(session, str(user["id"]), response)
    await session.commit()
    return AuthResponse(
        user=AuthUser(
            id=user["id"],
            name=user["name"],
            email=user["email"],
        )
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_database_session),
) -> Response:
    """Revoke the current session and clear its browser cookie."""

    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        await session.execute(
            text(
                """
                UPDATE user_sessions
                SET revoked_at = :revoked_at
                WHERE token_hash = :token_hash AND revoked_at IS NULL
                """
            ),
            {"revoked_at": datetime.now(UTC), "token_hash": token_hash},
        )
        await session.commit()

    response.delete_cookie(settings.session_cookie_name, path="/")
    return response
