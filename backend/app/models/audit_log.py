from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLogEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The audit trail required by spec section 19.

    Records every manual decision: old value, new value, user identity, timestamp and
    reason. Written by `app.services.audit_trail.record`; never edited or deleted.
    """

    __tablename__ = "audit_log_entries"

    audit_id: Mapped[str | None] = mapped_column(ForeignKey("audits.id"), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
