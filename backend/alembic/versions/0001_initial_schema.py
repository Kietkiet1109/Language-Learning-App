"""Create the initial Prononcia application schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-08
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL supplies UUID values without requiring the application to
    # generate identifiers before inserting a row.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_users_name_not_blank"),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_normalized"),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
        sa.CheckConstraint("expires_at > created_at", name="ck_user_sessions_expiry_after_creation"),
        sa.CheckConstraint("revoked_at IS NULL OR revoked_at >= created_at", name="ck_user_sessions_revoked_after_creation"),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
        sa.CheckConstraint("expires_at > created_at", name="ck_password_reset_expiry_after_creation"),
        sa.CheckConstraint("used_at IS NULL OR used_at >= created_at", name="ck_password_reset_used_after_creation"),
    )

    op.create_table(
        "media_sources",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("language_code", sa.Text(), server_default=sa.text("'fr'"), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'submitted'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_media_sources_id_user_id"),
        sa.CheckConstraint("source_type IN ('youtube', 'audio')", name="ck_media_sources_source_type"),
        sa.CheckConstraint("language_code = 'fr'", name="ck_media_sources_language_french"),
        sa.CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="ck_media_sources_duration_nonnegative"),
        sa.CheckConstraint("status IN ('submitted', 'processing', 'ready', 'failed')", name="ck_media_sources_status"),
        sa.CheckConstraint("btrim(source_url) <> ''", name="ck_media_sources_url_not_blank"),
    )

    op.create_table(
        "media_processing_jobs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("media_source_id", sa.UUID(), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["media_source_id"], ["media_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("job_type IN ('download', 'transcription', 'segmentation', 'cleanup')", name="ck_media_processing_jobs_type"),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_media_processing_jobs_status"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_media_processing_jobs_attempt_count_nonnegative"),
        sa.CheckConstraint("started_at IS NULL OR started_at >= created_at", name="ck_media_processing_jobs_started_after_creation"),
        sa.CheckConstraint("completed_at IS NULL OR completed_at >= created_at", name="ck_media_processing_jobs_completed_after_creation"),
    )

    op.create_table(
        "transcripts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("media_source_id", sa.UUID(), nullable=False),
        sa.Column("language_code", sa.Text(), server_default=sa.text("'fr'"), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("transcription_model", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["media_source_id"], ["media_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("language_code = 'fr'", name="ck_transcripts_language_french"),
        sa.CheckConstraint("btrim(full_text) <> ''", name="ck_transcripts_full_text_not_blank"),
    )

    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("transcript_id", sa.UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("start_seconds", sa.Numeric(), nullable=False),
        sa.Column("end_seconds", sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transcript_id", "sequence_number", name="uq_transcript_segments_sequence"),
        sa.CheckConstraint("sequence_number > 0", name="ck_transcript_segments_sequence_positive"),
        sa.CheckConstraint("btrim(text) <> ''", name="ck_transcript_segments_text_not_blank"),
        sa.CheckConstraint("btrim(normalized_text) <> ''", name="ck_transcript_segments_normalized_text_not_blank"),
        sa.CheckConstraint("start_seconds >= 0", name="ck_transcript_segments_start_nonnegative"),
        sa.CheckConstraint("end_seconds > start_seconds", name="ck_transcript_segments_end_after_start"),
    )

    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("media_source_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'started'"), nullable=False),
        sa.Column("overall_score", sa.Numeric(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["media_source_id", "user_id"], ["media_sources.id", "media_sources.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('started', 'in_progress', 'completed', 'abandoned')", name="ck_practice_sessions_status"),
        sa.CheckConstraint("overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 100)", name="ck_practice_sessions_score_range"),
        sa.CheckConstraint("completed_at IS NULL OR completed_at >= started_at", name="ck_practice_sessions_completed_after_start"),
        sa.CheckConstraint("saved_at IS NULL OR saved_at >= started_at", name="ck_practice_sessions_saved_after_start"),
        sa.CheckConstraint("status <> 'completed' OR completed_at IS NOT NULL", name="ck_practice_sessions_completed_has_timestamp"),
    )

    op.create_table(
        "sentence_attempts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("practice_session_id", sa.UUID(), nullable=False),
        sa.Column("transcript_segment_id", sa.UUID(), nullable=False),
        sa.Column("recording_path", sa.Text(), nullable=True),
        sa.Column("learner_transcription", sa.Text(), nullable=True),
        sa.Column("score", sa.Numeric(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["practice_session_id"], ["practice_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_segment_id"], ["transcript_segments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_sentence_attempts_score_range"),
    )

    op.create_table(
        "sentence_attempt_missed_words",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sentence_attempt_id", sa.UUID(), nullable=False),
        sa.Column("word", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["sentence_attempt_id"], ["sentence_attempts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("btrim(word) <> ''", name="ck_sentence_attempt_missed_words_not_blank"),
        sa.CheckConstraint("position IS NULL OR position >= 0", name="ck_sentence_attempt_missed_words_position_nonnegative"),
    )

    op.create_index("ix_media_sources_user_created_at", "media_sources", ["user_id", "created_at"])
    op.create_index("ix_media_processing_jobs_source_status", "media_processing_jobs", ["media_source_id", "status"])
    op.create_index("ix_transcripts_source_created_at", "transcripts", ["media_source_id", "created_at"])
    op.create_index("ix_practice_sessions_user_started_at", "practice_sessions", ["user_id", "started_at"])
    op.create_index("ix_sentence_attempts_session_created_at", "sentence_attempts", ["practice_session_id", "created_at"])
    op.create_index("ix_sentence_attempt_missed_words_attempt", "sentence_attempt_missed_words", ["sentence_attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_sentence_attempt_missed_words_attempt", table_name="sentence_attempt_missed_words")
    op.drop_index("ix_sentence_attempts_session_created_at", table_name="sentence_attempts")
    op.drop_index("ix_practice_sessions_user_started_at", table_name="practice_sessions")
    op.drop_index("ix_transcripts_source_created_at", table_name="transcripts")
    op.drop_index("ix_media_processing_jobs_source_status", table_name="media_processing_jobs")
    op.drop_index("ix_media_sources_user_created_at", table_name="media_sources")

    op.drop_table("sentence_attempt_missed_words")
    op.drop_table("sentence_attempts")
    op.drop_table("practice_sessions")
    op.drop_table("transcript_segments")
    op.drop_table("transcripts")
    op.drop_table("media_processing_jobs")
    op.drop_table("media_sources")
    op.drop_table("password_reset_tokens")
    op.drop_table("user_sessions")
    op.drop_table("users")
