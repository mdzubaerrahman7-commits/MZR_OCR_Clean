from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TimestampedORMBase


class SourceDocumentOut(TimestampedORMBase):
    audit_id: str
    document_type: str
    original_filename: str
    checksum_sha256: str
    content_type: str | None = None
    sheet_names: list[str] | None = None
    uploaded_by: str
    uploaded_at: datetime
    supersedes_id: str | None = None


class HeaderDetectionOut(BaseModel):
    sheet_name: str
    header_row_index: int
    headers: list[str]


class MappingSuggestionOut(BaseModel):
    source_header: str
    suggested_target_field: str | None
    confidence: float


class ColumnMappingSuggestionsOut(BaseModel):
    sheet_name: str
    header_row_index: int
    available_target_fields: list[str]
    suggestions: list[MappingSuggestionOut]
    preview_rows: list[dict]


class ConfirmedMappingEntry(BaseModel):
    source_header: str
    target_field: str


class ConfirmMappingRequest(BaseModel):
    sheet_name: str
    mappings: list[ConfirmedMappingEntry]
    save_as_template_name: str | None = None


class DocumentColumnMappingOut(BaseModel):
    id: str
    sheet_name: str | None
    source_header: str
    target_field: str
    confirmed_by: str


class MappingTemplateFieldOut(BaseModel):
    source_header: str
    target_field: str
    sequence_no: int


class MappingTemplateOut(TimestampedORMBase):
    name: str
    document_type: str
    company_id: str | None
    fields: list[MappingTemplateFieldOut]
