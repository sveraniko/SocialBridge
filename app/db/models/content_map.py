import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContentMap(Base):
    __tablename__ = "sb_content_map"
    __table_args__ = (
        UniqueConstraint("channel", "content_ref", name="uq_sb_content_map_channel_content_ref"),
        UniqueConstraint("slug", name="uq_sb_content_map_slug"),
        CheckConstraint("char_length(slug) between 1 and 64", name="ck_sb_content_map_slug_len"),
        CheckConstraint("slug ~ '^[a-z0-9_-]+$'", name="ck_sb_content_map_slug_re"),
        CheckConstraint("slug = lower(slug)", name="ck_sb_content_map_slug_lower"),
        CheckConstraint(
            "start_param is null or char_length(start_param) <= 64",
            name="ck_sb_content_map_start_param_len",
        ),
        CheckConstraint(
            "start_param is null or start_param ~ '^[A-Za-z0-9_-]+$'",
            name="ck_sb_content_map_start_param_re",
        ),
        Index("ix_sb_content_map_channel_active", "channel", "is_active"),
        Index("ix_sb_content_map_updated_at", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    content_ref: Mapped[str] = mapped_column(Text, nullable=False)
    start_param: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
