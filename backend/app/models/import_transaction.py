from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Classification, ExcessStatus, MatchStatus, ReviewStatus


class ImportTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spec section 8, extended with the classification/matching/conversion/excess
    working fields those engines populate. Nothing here is hand-edited; every
    non-null derived field was written by a specific engine and can be recomputed."""

    __tablename__ = "import_transactions"

    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    be_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    be_date: Mapped[date] = mapped_column(Date, nullable=False)
    import_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lc_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    item_description: Mapped[str] = mapped_column(String(1000), nullable=False)
    hs_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    declared_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    declared_unit: Mapped[str] = mapped_column(String(32), nullable=False)

    # M06 — Entitlement matching
    entitlement_item_id: Mapped[str | None] = mapped_column(ForeignKey("entitlement_items.id"), nullable=True)
    match_status: Mapped[str] = mapped_column(String(32), nullable=False, default=MatchStatus.UNMATCHED)
    match_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    match_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # M07 — Quantity & currency conversion (evidence-driven; null == not yet convertible)
    entitlement_quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    entitlement_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kg_quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    original_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    original_currency_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    usd_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    assessable_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    conversion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # M05 — Classification
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default=Classification.UNKNOWN)
    classification_confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)

    # M08 — Excess detection
    non_entitled: Mapped[bool] = mapped_column(default=False, nullable=False)
    excess_status: Mapped[str] = mapped_column(String(32), nullable=False, default=ExcessStatus.NOT_APPLICABLE)
    excess_quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    allowed_quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    cumulative_quantity_after: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)

    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default=ReviewStatus.PENDING)

    entitlement_item: Mapped["EntitlementItem | None"] = relationship()
