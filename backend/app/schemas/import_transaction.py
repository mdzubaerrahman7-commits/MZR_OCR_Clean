from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import TimestampedORMBase


class ParseImportMisRequest(BaseModel):
    source_document_id: str
    sheet_name: str


class ParseImportMisResult(BaseModel):
    parsed_count: int
    in_period_count: int
    excluded_out_of_period_count: int
    classification_breakdown: dict[str, int]


class ImportTransactionOut(TimestampedORMBase):
    audit_id: str
    source_document_id: str
    source_row_number: int
    be_number: str
    be_date: date
    import_date: date | None = None
    lc_number: str | None = None
    invoice_number: str | None = None
    item_description: str
    hs_code: str
    declared_quantity: Decimal
    declared_unit: str

    entitlement_item_id: str | None = None
    match_status: str
    match_confidence: Decimal | None = None
    match_evidence: str | None = None

    entitlement_quantity: Decimal | None = None
    entitlement_unit: str | None = None
    kg_quantity: Decimal | None = None
    original_currency: str | None = None
    original_currency_value: Decimal | None = None
    usd_value: Decimal | None = None
    assessable_value: Decimal | None = None
    conversion_evidence: str | None = None

    classification: str
    classification_confidence: Decimal

    non_entitled: bool
    excess_status: str
    excess_quantity: Decimal | None = None
    allowed_quantity: Decimal | None = None
    cumulative_quantity_after: Decimal | None = None

    review_status: str


class ClassificationOverrideRequest(BaseModel):
    classification: str
    reason: str
