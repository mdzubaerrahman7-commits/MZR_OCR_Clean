from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BillOfEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spec section 9 — the authoritative source for transaction-specific quantity and
    currency conversion. Never invented: fields stay null until evidence is on file."""

    __tablename__ = "bill_of_entries"
    __table_args__ = (UniqueConstraint("audit_id", "be_number", name="uq_bill_of_entry_audit_number"),)

    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    be_number: Mapped[str] = mapped_column(String(64), nullable=False)
    be_date: Mapped[date] = mapped_column(Date, nullable=False)
    conversion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    exchange_rate_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessable_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)

    duty_components: Mapped[list["DutyComponent"]] = relationship(
        back_populates="bill_of_entry", cascade="all, delete-orphan"
    )


class DutyComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "duty_components"

    bill_of_entry_id: Mapped[str] = mapped_column(ForeignKey("bill_of_entries.id"), nullable=False, index=True)
    component_code: Mapped[str] = mapped_column(String(16), nullable=False)  # CD/RD/SD/VAT/AIT/AT/...
    rate: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False, default=0)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    calculated_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    source_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    bill_of_entry: Mapped["BillOfEntry"] = relationship(back_populates="duty_components")
