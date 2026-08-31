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

    # USD value of 1 unit of the transaction's original_currency, sourced from this B/E.
    # usd_value = original_currency_value * exchange_rate. Null means "no B/E rate on
    # file yet" — conversion_engine must not substitute a market rate (spec section 12).
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    exchange_rate_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # KG equivalent of 1 declared_unit, sourced from this B/E (spec section 11: "A KG
    # quantity must also be presented where required").
    kg_conversion_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    kg_conversion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # entitlement_unit quantity per 1 declared_unit, only needed when declared_unit !=
    # the matched entitlement item's unit.
    entitlement_conversion_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    entitlement_conversion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

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
