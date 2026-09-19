"""Dependencies for authenticated API requests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_database_session


async def get_current_user_id(
    request: Request,
    session: AsyncSession = Depends(get_database_session),
) -> UUID:
    """Return the user ID represented by the active session cookie."""

    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    result = await session.execute(
        text(
            """
            SELECT users.id
            FROM user_sessions
            JOIN users ON users.id = user_sessions.user_id
            WHERE user_sessions.token_hash = :token_hash
              AND user_sessions.revoked_at IS NULL
              AND user_sessions.expires_at > :now
              AND users.is_active = TRUE
            """
        ),
        {"token_hash": token_hash, "now": datetime.now(UTC)},
    )
    user_id = result.scalar_one_or_none()
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )

    await session.execute(
        text(
            """
            UPDATE user_sessions
            SET last_used_at = :now
            WHERE token_hash = :token_hash
            """
        ),
        {"token_hash": token_hash, "now": datetime.now(UTC)},
    )
    await session.commit()
    return UUID(str(user_id))
