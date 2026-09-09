"""Authentication endpoints for account creation and login."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from aiosmtplib.errors import SMTPException
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
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


def facebook_is_configured() -> bool:
    """Return whether the required Facebook OAuth settings are available."""

    return bool(
        settings.facebook_app_id and settings.facebook_app_secret
    )


def facebook_error_redirect(error_code: str) -> RedirectResponse:
    """Redirect the browser to Login with a safe, non-sensitive error code."""

    query = urlencode({"facebook_error": error_code})
    return RedirectResponse(
        url=f"{settings.frontend_origin}/login?{query}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


async def fetch_facebook_profile(code: str) -> dict[str, str]:
    """Exchange a Facebook code and return the verified basic profile."""

    if not facebook_is_configured():
        raise RuntimeError("Facebook OAuth is not configured.")

    graph_base_url = (
        f"https://graph.facebook.com/{settings.facebook_graph_version}"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_response = await client.get(
            f"{graph_base_url}/oauth/access_token",
            params={
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "redirect_uri": settings.facebook_redirect_uri,
                "code": code,
            },
        )
        token_response.raise_for_status()
        token_body = token_response.json()
        access_token = token_body.get("access_token")
        if not isinstance(access_token, str):
            raise ValueError("Facebook did not return an access token.")

        app_access_token = (
            f"{settings.facebook_app_id}|{settings.facebook_app_secret}"
        )
        debug_response = await client.get(
            f"{graph_base_url}/debug_token",
            params={
                "input_token": access_token,
                "access_token": app_access_token,
            },
        )
        debug_response.raise_for_status()
        debug_data = debug_response.json().get("data", {})
        if (
            debug_data.get("is_valid") is not True
            or debug_data.get("app_id") != settings.facebook_app_id
        ):
            raise ValueError("Facebook returned an invalid access token.")

        profile_response = await client.get(
            f"{graph_base_url}/me",
            params={
                "fields": "id,name,email",
                "access_token": access_token,
            },
        )
        profile_response.raise_for_status()
        profile = profile_response.json()

    provider_user_id = profile.get("id")
    provider_name = profile.get("name")
    provider_email = profile.get("email")
    if not all(
        isinstance(value, str)
        for value in (provider_user_id, provider_name, provider_email)
    ):
        raise ValueError("Facebook did not provide a complete user profile.")

    return {
        "provider_user_id": provider_user_id,
        "name": provider_name,
        "email": normalize_email(provider_email),
    }


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


@router.get("/facebook/login")
async def facebook_login() -> RedirectResponse:
    """Start Facebook OAuth and store a short-lived CSRF state cookie."""

    if not facebook_is_configured():
        return facebook_error_redirect("facebook_not_configured")

    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": settings.facebook_app_id,
            "redirect_uri": settings.facebook_redirect_uri,
            "state": state,
            "scope": "public_profile,email",
            "response_type": "code",
        }
    )
    redirect_response = RedirectResponse(
        url=(
            f"https://www.facebook.com/"
            f"{settings.facebook_graph_version}/dialog/oauth?{query}"
        ),
        status_code=status.HTTP_302_FOUND,
    )
    redirect_response.set_cookie(
        key=settings.facebook_state_cookie_name,
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return redirect_response


@router.get("/facebook/callback")
async def facebook_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_database_session),
) -> RedirectResponse:
    """Complete Facebook OAuth and create a normal Prononcia session."""

    state_cookie = request.cookies.get(settings.facebook_state_cookie_name)
    if (
        not state
        or not state_cookie
        or not secrets.compare_digest(state, state_cookie)
    ):
        return facebook_error_redirect("facebook_state_invalid")

    if error or not code:
        return facebook_error_redirect("facebook_cancelled")

    try:
        profile = await fetch_facebook_profile(code)
    except (httpx.HTTPError, ValueError, RuntimeError):
        logger.exception("Facebook OAuth profile validation failed.")
        return facebook_error_redirect("facebook_login_failed")

    identity_result = await session.execute(
        text(
            """
            SELECT users.id, users.name, users.email
            FROM auth_identities
            JOIN users ON users.id = auth_identities.user_id
            WHERE auth_identities.provider = 'facebook'
              AND auth_identities.provider_user_id = :provider_user_id
              AND users.is_active = true
            """
        ),
        {"provider_user_id": profile["provider_user_id"]},
    )
    user = identity_result.mappings().one_or_none()

    try:
        if user is None:
            user_result = await session.execute(
                text(
                    """
                    SELECT id, name, email
                    FROM users
                    WHERE email = :email AND is_active = true
                    """
                ),
                {"email": profile["email"]},
            )
            user = user_result.mappings().one_or_none()

        if user is None:
            user_result = await session.execute(
                text(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (:name, :email, NULL)
                    RETURNING id, name, email
                    """
                ),
                {
                    "name": normalize_name(profile["name"]),
                    "email": profile["email"],
                },
            )
            user = user_result.mappings().one()

        identity_exists = await session.execute(
            text(
                """
                SELECT id
                FROM auth_identities
                WHERE provider = 'facebook'
                  AND provider_user_id = :provider_user_id
                """
            ),
            {"provider_user_id": profile["provider_user_id"]},
        )
        if identity_exists.scalar_one_or_none() is None:
            await session.execute(
                text(
                    """
                    INSERT INTO auth_identities (
                        user_id, provider, provider_user_id, provider_email
                    )
                    VALUES (
                        :user_id, 'facebook', :provider_user_id,
                        :provider_email
                    )
                    """
                ),
                {
                    "user_id": user["id"],
                    "provider_user_id": profile["provider_user_id"],
                    "provider_email": profile["email"],
                },
            )

        redirect_response = RedirectResponse(
            url=settings.frontend_origin,
            status_code=status.HTTP_303_SEE_OTHER,
        )
        await create_session(session, str(user["id"]), redirect_response)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.exception("Facebook identity could not be persisted.")
        return facebook_error_redirect("facebook_account_link_failed")

    redirect_response.delete_cookie(
        settings.facebook_state_cookie_name,
        path="/",
    )
    return redirect_response


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
