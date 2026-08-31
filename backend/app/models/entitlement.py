from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EntitlementGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spec section 7. Sequence is authoritative and must never be re-sorted."""

    __tablename__ = "entitlement_groups"

    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    group_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)

    items: Mapped[list["EntitlementItem"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="EntitlementItem.sequence_no"
    )


class EntitlementItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Spec section 7. total_entitlement_qty = annual + enhanced, computed, never hand-entered."""

    __tablename__ = "entitlement_items"

    group_id: Mapped[str] = mapped_column(ForeignKey("entitlement_groups.id"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    material_name: Mapped[str] = mapped_column(String(500), nullable=False)
    hs_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entitlement_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    annual_entitlement_qty: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    enhanced_entitlement_qty: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    total_entitlement_qty: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    group: Mapped["EntitlementGroup"] = relationship(back_populates="items")
