"""Add English translations to transcript segments.

Revision ID: 0004_add_english_text
Revises: 0003_allow_google_identity
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_english_text"
down_revision: Union[str, Sequence[str], None] = "0003_allow_google_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store the optional English translation for each sentence."""

    op.add_column(
        "transcript_segments",
        sa.Column("english_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove sentence translations."""

    op.drop_column("transcript_segments", "english_text")
