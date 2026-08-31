from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuditStatus


class Audit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audits"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    audit_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    audit_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    audit_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    entitlement_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    entitlement_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default=AuditStatus.DRAFT)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="audits")  # noqa: F821
