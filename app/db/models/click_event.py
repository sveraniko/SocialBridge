import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClickEvent(Base):
    __tablename__ = "sb_click_event"
    __table_args__ = (
        CheckConstraint("slug ~ '^[a-z0-9_-]+$'", name="ck_sb_click_event_slug_re"),
        CheckConstraint("ip_hash is null or ip_hash ~ '^[0-9a-f]{64}$'", name="ck_sb_click_event_ip_hash"),
        Index("ix_sb_click_event_created_at", "created_at"),
        Index("ix_sb_click_event_slug_created_at", "slug", "created_at"),
        Index("ix_sb_click_event_content_map_created_at", "content_map_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_map_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sb_content_map.id", ondelete="SET NULL"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    referer: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
