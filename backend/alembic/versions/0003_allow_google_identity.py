"""Allow Google identities in external authentication records.

Revision ID: 0003_allow_google_identity
Revises: 0002_add_auth_identities
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0003_allow_google_identity"
down_revision: Union[str, Sequence[str], None] = "0002_add_auth_identities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Expand supported external authentication providers."""

    op.drop_constraint(
        "ck_auth_identities_provider",
        "auth_identities",
        type_="check",
    )
    op.create_check_constraint(
        "ck_auth_identities_provider",
        "auth_identities",
        "provider IN ('facebook', 'google')",
    )


def downgrade() -> None:
    """Restrict identities back to Facebook."""

    op.drop_constraint(
        "ck_auth_identities_provider",
        "auth_identities",
        type_="check",
    )
    op.create_check_constraint(
        "ck_auth_identities_provider",
        "auth_identities",
        "provider IN ('facebook')",
    )
