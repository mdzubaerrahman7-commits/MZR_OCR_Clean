from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.models.enums import DocumentType


class SourceDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Layer A raw evidence: an uploaded file, stored immutably.

    A re-upload never overwrites a row — it inserts a new SourceDocument and points
    `supersedes_id` at the previous version, so every historical upload stays reachable.
    """

    __tablename__ = "source_documents"

    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False, default=DocumentType.OTHER)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sheet_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)

    column_mappings: Mapped[list["DocumentColumnMapping"]] = relationship(
        back_populates="source_document", cascade="all, delete-orphan"
    )


class ColumnMappingTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A reusable, named set of header -> canonical-field mappings (spec M03)."""

    __tablename__ = "column_mapping_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    fields: Mapped[list["ColumnMappingTemplateField"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="ColumnMappingTemplateField.sequence_no"
    )


class ColumnMappingTemplateField(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "column_mapping_template_fields"

    template_id: Mapped[str] = mapped_column(ForeignKey("column_mapping_templates.id"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_header: Mapped[str] = mapped_column(String(255), nullable=False)
    target_field: Mapped[str] = mapped_column(String(128), nullable=False)

    template: Mapped["ColumnMappingTemplate"] = relationship(back_populates="fields")


class DocumentColumnMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The confirmed mapping actually applied to one uploaded document (M03: auditor confirmation)."""

    __tablename__ = "document_column_mappings"

    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), nullable=False, index=True)
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_header: Mapped[str] = mapped_column(String(255), nullable=False)
    target_field: Mapped[str] = mapped_column(String(128), nullable=False)
    confirmed_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    source_document: Mapped["SourceDocument"] = relationship(back_populates="column_mappings")
