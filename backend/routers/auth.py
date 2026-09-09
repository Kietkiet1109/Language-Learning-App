"""Authentication endpoints for account creation and login."""

import hashlib
from datetime import UTC, datetime

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

from backend.auth import create_session_token, hash_password, verify_password
from backend.config import settings
from backend.database import get_database_session
from backend.schemas import AuthResponse, AuthUser, LoginRequest, SignupRequest


router = APIRouter(prefix="/auth", tags=["authentication"])


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
