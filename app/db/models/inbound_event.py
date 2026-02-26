import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InboundEvent(Base):
    __tablename__ = "sb_inbound_event"
    __table_args__ = (
        UniqueConstraint("channel", "payload_hash", name="uq_sb_inbound_event_channel_payload_hash"),
        CheckConstraint("payload_hash ~ '^[0-9a-f]{64}$'", name="ck_sb_inbound_event_payload_hash"),
        CheckConstraint(
            "resolved_start_param is null or char_length(resolved_start_param) <= 64",
            name="ck_sb_inbound_event_start_param_len",
        ),
        CheckConstraint(
            "resolved_slug is null or resolved_slug ~ '^[a-z0-9_-]+$'",
            name="ck_sb_inbound_event_slug_re",
        ),
        Index("ix_sb_inbound_event_created_at_desc", "created_at"),
        Index("ix_sb_inbound_event_channel_created_at", "channel", "created_at"),
        Index("ix_sb_inbound_event_result_created_at", "result", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    mc_contact_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mc_flow_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mc_trigger: Mapped[str | None] = mapped_column(String(128), nullable=True)
    text_preview: Mapped[str | None] = mapped_column(String(256), nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    resolved_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_start_param: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_min: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
