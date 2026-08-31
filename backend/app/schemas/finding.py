from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import TimestampedORMBase


class FindingOut(TimestampedORMBase):
    audit_id: str
    finding_code: str
    issue_type: str
    evidence: str
    bill_of_entry_id: str | None = None
    import_transaction_id: str | None = None
    entitlement_item_id: str | None = None
    material_name: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    value: Decimal | None = None
    demand_amount: Decimal | None = None
    review_status: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class GenerateFindingsResult(BaseModel):
    created_count: int
    updated_count: int
    removed_count: int
    total_findings: int


class FindingReviewRequest(BaseModel):
    decision: str  # approved | rejected | under_review
    reason: str | None = None
