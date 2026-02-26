"""baseline init

Revision ID: 0001_baseline_init
Revises:
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_baseline_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sb_content_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("content_ref", sa.Text(), nullable=False),
        sa.Column("start_param", sa.String(length=64), nullable=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("char_length(slug) between 1 and 64", name="ck_sb_content_map_slug_len"),
        sa.CheckConstraint("slug ~ '^[a-z0-9_-]+$'", name="ck_sb_content_map_slug_re"),
        sa.CheckConstraint("slug = lower(slug)", name="ck_sb_content_map_slug_lower"),
        sa.CheckConstraint("start_param is null or char_length(start_param) <= 64", name="ck_sb_content_map_start_param_len"),
        sa.CheckConstraint("start_param is null or start_param ~ '^[A-Za-z0-9_-]+$'", name="ck_sb_content_map_start_param_re"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel", "content_ref", name="uq_sb_content_map_channel_content_ref"),
        sa.UniqueConstraint("slug", name="uq_sb_content_map_slug"),
    )
    op.create_index("ix_sb_content_map_channel_active", "sb_content_map", ["channel", "is_active"])
    op.create_index("ix_sb_content_map_updated_at", "sb_content_map", ["updated_at"])

    op.create_table(
        "sb_inbound_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("content_ref", sa.Text(), nullable=True),
        sa.Column("mc_contact_id", sa.String(length=128), nullable=True),
        sa.Column("mc_flow_id", sa.String(length=128), nullable=True),
        sa.Column("mc_trigger", sa.String(length=128), nullable=True),
        sa.Column("text_preview", sa.String(length=256), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("resolved_slug", sa.String(length=64), nullable=True),
        sa.Column("resolved_start_param", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("payload_min", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("payload_hash ~ '^[0-9a-f]{64}$'", name="ck_sb_inbound_event_payload_hash"),
        sa.CheckConstraint("resolved_slug is null or resolved_slug ~ '^[a-z0-9_-]+$'", name="ck_sb_inbound_event_slug_re"),
        sa.CheckConstraint("resolved_start_param is null or char_length(resolved_start_param) <= 64", name="ck_sb_inbound_event_start_param_len"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel", "payload_hash", name="uq_sb_inbound_event_channel_payload_hash"),
    )
    op.create_index("ix_sb_inbound_event_created_at_desc", "sb_inbound_event", ["created_at"])
    op.create_index("ix_sb_inbound_event_channel_created_at", "sb_inbound_event", ["channel", "created_at"])
    op.create_index("ix_sb_inbound_event_result_created_at", "sb_inbound_event", ["result", "created_at"])

    op.create_table(
        "sb_click_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_map_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("referer", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("ip_hash is null or ip_hash ~ '^[0-9a-f]{64}$'", name="ck_sb_click_event_ip_hash"),
        sa.CheckConstraint("slug ~ '^[a-z0-9_-]+$'", name="ck_sb_click_event_slug_re"),
        sa.ForeignKeyConstraint(["content_map_id"], ["sb_content_map.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sb_click_event_created_at", "sb_click_event", ["created_at"])
    op.create_index("ix_sb_click_event_slug_created_at", "sb_click_event", ["slug", "created_at"])
    op.create_index("ix_sb_click_event_content_map_created_at", "sb_click_event", ["content_map_id", "created_at"])


def downgrade() -> None:
    op.drop_table("sb_click_event")
    op.drop_table("sb_inbound_event")
    op.drop_table("sb_content_map")
