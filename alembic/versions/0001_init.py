from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "uploads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("content_type", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.BigInteger),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("checksum_sha256", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_check_constraint("uploads_status_chk", "uploads", "status in ('receiving','processing','ready','failed')")
    op.create_table(
        "audio_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("upload_id", UUID(as_uuid=True), sa.ForeignKey("uploads.id"), unique=True),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("sample_rate", sa.Integer),
        sa.Column("channels", sa.Integer),
        sa.Column("duration_s", sa.Numeric),
        sa.Column("format", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("upload_id", UUID(as_uuid=True), sa.ForeignKey("uploads.id")),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text),
        sa.Column("payload", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_jobs_upload_type", "jobs", ["upload_id", "type"])
    op.create_check_constraint("jobs_status_chk", "jobs", "status in ('queued','in_progress','done','failed')")
    op.create_table(
        "segments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("audio_id", UUID(as_uuid=True), sa.ForeignKey("audio_files.id")),
        sa.Column("start_ms", sa.Integer, nullable=False),
        sa.Column("end_ms", sa.Integer, nullable=False),
        sa.Column("rms", sa.Float),
        sa.Column("zcr", sa.Float),
        sa.Column("transcript", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "upload_chunks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("upload_id", UUID(as_uuid=True), sa.ForeignKey("uploads.id"), index=True),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("range_start", sa.BigInteger, nullable=False),
        sa.Column("range_end", sa.BigInteger, nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("sha256", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_chunk_unique", "upload_chunks", ["upload_id", "chunk_index"])

def downgrade():
    op.drop_table("upload_chunks")
    op.drop_table("segments")
    op.drop_table("jobs")
    op.drop_table("audio_files")
    op.drop_table("uploads")