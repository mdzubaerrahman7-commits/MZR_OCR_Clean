from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bin_number: Mapped[str] = mapped_column(String(64), nullable=False)
    bond_license_number: Mapped[str] = mapped_column(String(64), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(64), nullable=False, default="bonded_warehouse")
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    audits: Mapped[list["Audit"]] = relationship(back_populates="company", cascade="all, delete-orphan")  # noqa: F821
