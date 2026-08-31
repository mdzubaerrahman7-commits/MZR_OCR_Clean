from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class GeneratedReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spec section 19: 'Generated reports should record source audit ID and generation time.'"""

    __tablename__ = "generated_reports"

    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    output_code: Mapped[str] = mapped_column(String(32), nullable=False)  # OUTPUT_01 .. OUTPUT_07
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    generated_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
