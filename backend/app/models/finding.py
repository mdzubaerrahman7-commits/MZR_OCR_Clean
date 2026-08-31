from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FindingIssueType, FindingReviewStatus


class Finding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spec OUTPUT 07 — Import Audit Findings Register."""

    __tablename__ = "findings"

    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    finding_code: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(32), nullable=False, default=FindingIssueType.OTHER)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)

    bill_of_entry_id: Mapped[str | None] = mapped_column(ForeignKey("bill_of_entries.id"), nullable=True)
    import_transaction_id: Mapped[str | None] = mapped_column(ForeignKey("import_transactions.id"), nullable=True)
    entitlement_item_id: Mapped[str | None] = mapped_column(ForeignKey("entitlement_items.id"), nullable=True)

    material_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    demand_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)

    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default=FindingReviewStatus.OPEN)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    import_transaction: Mapped["ImportTransaction | None"] = relationship(viewonly=True)  # noqa: F821
