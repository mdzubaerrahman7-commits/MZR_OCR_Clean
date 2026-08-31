from pydantic import BaseModel

from app.schemas.import_transaction import ImportTransactionOut


class ClassifyResult(BaseModel):
    reclassified_count: int
    skipped_manual_override_count: int
    classification_breakdown: dict[str, int]


class DetectExcessResult(BaseModel):
    non_entitled_marked_count: int
    entitlement_items_processed: int
    within_entitlement_count: int
    partial_excess_count: int
    full_excess_count: int
    skipped_unconverted_count: int


class ExceptionDashboardOut(BaseModel):
    non_entitled_count: int
    review_required_match_count: int
    unknown_classification_count: int
    partial_excess_count: int
    full_excess_count: int
    conversion_incomplete_count: int
    non_entitled_transactions: list[ImportTransactionOut]
    review_required_transactions: list[ImportTransactionOut]
    excess_transactions: list[ImportTransactionOut]
    conversion_incomplete_transactions: list[ImportTransactionOut]
